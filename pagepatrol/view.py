from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from sqlalchemy import func
from .model import Term, SafeArticle, SafePhrase, SafePhraseArtcle, TermNotInArticle
from . import database
from .wikipedia import wiki_search, hit_count, get_content
import logging
import re

bp = Blueprint('view', __name__)

def init_app(app):
    app.register_blueprint(bp)

def find_term_in_content(term, content, context=100):
    re_term = re.compile('(.{,' + str(context) + '})(' +
                         term + ')(.{,' + str(context) + '})', re.I | re.S)
    return re_term.findall(content)

@bp.route("/")
def index():
    order = request.args.get('order')
    if order:
        session['order'] = order
    else:
        order = session.get('order')
    q = Term.query.order_by(Term.total_hits if order == 'hits' else Term.term)

    sa = dict(database.session.query(SafeArticle.term,
                                     func.count(SafeArticle.title))
                      .group_by(SafeArticle.term))
    sp = dict(database.session.query(SafePhrase.term,
                                     func.count(SafePhrase.phrase))
                      .group_by(SafePhrase.term))

    return render_template('index.html', terms=q, sa=sa, sp=sp)

@bp.route("/new", methods=['GET', 'POST'])
def new_term():
    term = request.form.get('term')
    if request.method == 'POST' and term:
        q = 'insource:"{}"'.format(term)
        t = Term(term=term, total_hits=hit_count(q))
        database.session.add(t)
        database.session.commit()
        flash('new term added: {}'.format(term))
        return redirect(url_for('.index'))
    return render_template('new_term.html')

@bp.route("/mark_as_safe/<term>", methods=['POST'])
def mark_as_safe(term):
    t = Term.query.get(term.replace('_', ' '))
    title = request.form['title']
    t.safe_articles.add(SafeArticle(title=title))
    database.session.commit()
    return jsonify(success=True)

@bp.route("/mark_safe")
def mark_safe():
    title = request.args['title']
    term = request.args['term']
    offset = request.args.get('offset')

    t = Term.query.get(term)
    t.safe_articles.add(SafeArticle(title=title))
    database.session.commit()

    return redirect(url_for('.patrol', term=term, offset=offset))

@bp.route("/safe_articles/<term>")
def safe_articles(term):
    t = Term.query.get(term.replace('_', ' '))
    safe_articles = sorted({doc.title for doc in t.safe_articles})
    return render_template('safe_articles.html', term=t,
                           safe_articles=safe_articles)

@bp.route("/safe_phrases/<term>")
def safe_phrases(term):
    t = Term.query.get(term.replace('_', ' '))
    safe_phrases = sorted({safe.phrase for safe in t.safe_phrases})
    return render_template('safe_phrases.html', term=t,
                           safe_phrases=safe_phrases)

@bp.route("/add_safe_phrase/<term>", methods=['POST'])
def add_safe_phrase(term):
    t = Term.query.get(term.replace('_', ' '))
    phrase = request.form['phrase']
    t.safe_phrases.add(SafePhrase(phrase=phrase))
    database.session.commit()
    flash('"{}" added as safe phrase for "{}"'.format(phrase, t.term))
    return redirect(url_for('.safe_phrases', term=term))

@bp.route("/remove_safe_article/<term>", methods=['POST'])
def remove_safe_article(term):
    term_clean = term.replace('_', ' ')
    t = Term.query.get(term_clean)
    article = request.form['item']
    sa = SafeArticle.query.filter_by(term=term_clean, title=article).one()
    database.session.delete(sa)
    database.session.commit()
    flash('"{}" is no longer a safe article for "{}"'.format(article, t.term))
    return redirect(url_for('.safe_articles', term=term))

@bp.route("/remove_safe_phrase/<term>", methods=['POST'])
def remove_safe_phrase(term):
    term_clean = term.replace('_', ' ')
    t = Term.query.get(term_clean)
    phrase = request.form['item']
    sp = SafePhrase.query.filter_by(term=term_clean, phrase=phrase).one()
    database.session.delete(sp)
    database.session.commit()
    flash('"{}" is no longer a safe phrase for "{}"'.format(phrase, t.term))
    return redirect(url_for('.safe_phrases', term=term))

@bp.route("/patrol/<term>")
def patrol(term):
    skip = set()
    t = Term.query.get(term.replace('_', ' '))
    database.session.expire(t)
    skip |= {doc.title for doc in t.safe_articles}

    q = (database.session.query(SafePhraseArtcle.title)
                         .filter_by(term=t.term)
                         .distinct())
    skip |= {row[0] for row in q}

    q = (database.session.query(TermNotInArticle.title)
                         .filter_by(term=t.term)
                         .distinct())
    skip |= {row[0] for row in q}

    return render_template('stream.html',
                           url_term=term,
                           term=t,
                           skip=list(skip))

@bp.route("/old_patrol/<term>")
def old_patrol(term):
    offset = int(request.args.get('offset') or 0)
    t = Term.query.get(term.replace('_', ' '))
    database.session.expire(t)

    safe_articles = {doc.title for doc in t.safe_articles}

    results = wiki_search(t.get_query(), offset=offset)
    if results.total_hits != t.total_hits:
        t.total_hits = results.total_hits
        database.session.commit()

    pattern = '|'.join(re.escape(safe.phrase) for safe in t.safe_phrases)
    re_phrase = re.compile('(' + pattern + ')')
    total_hits = results.total_hits

    docs = []
    for doc in results.docs:
        if doc['title'] in safe_articles:
            logging.info('safe article:', doc['title'])
            total_hits -= 1
            continue
        if t.term.lower() not in doc['text'].lower():
            logging.info('term not in article:', doc['title'])
            total_hits -= 1
            continue
        if pattern and re_phrase.search(doc['text']):
            logging.info('safe phrase:', doc['title'])
            total_hits -= 1
            continue

        docs.append(doc)

    return render_template('search.html',
                           offset=offset,
                           total_hits=total_hits,
                           results=results,
                           docs=docs,
                           safe_articles=safe_articles,
                           find_term_in_content=find_term_in_content,
                           term=t)

def escape_phrase(phrase):
    c1 = phrase[0]
    if not c1.isalpha():
        return re.escape(phrase)
    return '[{}{}]'.format(c1.lower(), c1.upper()) + re.escape(phrase[1:])

def lc_first(s):
    return s[0].lower() + s[1:]

@bp.route('/check_titles/<term>')
def check_titles(term):
    skip = []
    t = Term.query.get(term.replace('_', ' '))
    database.session.expire(t)
    lc_term = t.term.lower()
    titles = request.args.getlist('titles[]')
    if not titles:
        return jsonify(skip=skip)

    lookup = {lc_first(safe.phrase): safe.phrase for safe in t.safe_phrases}

    pattern = '|'.join(escape_phrase(phrase) for phrase in lookup.values())
    re_phrase = re.compile('(' + pattern + ')')
    pages = get_content(titles)
    commit_needed = False
    for page in pages:
        title = page['title']
        content = page['revisions'][0]['content']
        if lc_term not in content.lower():
            i = TermNotInArticle(title=title, term=t.term)
            database.session.merge(i)
            commit_needed = True
            skip.append(title)
        if pattern:
            m = re_phrase.search(content)
            if m:
                phrase = lookup[lc_first(m.group(1))]
                i = SafePhraseArtcle(phrase=phrase, title=title, term=t.term)
                database.session.merge(i)
                commit_needed = True
                skip.append(page['title'])
    if commit_needed:
        database.session.commit()
    return jsonify(skip=skip)
