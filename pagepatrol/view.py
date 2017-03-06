from flask import Blueprint, request, render_template, redirect, url_for, flash
from sqlalchemy import func
from .model import Term, SafeArticle, SafePhrase
from .database import session
from .wikipedia import wiki_search, hit_count
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
    q = Term.query.order_by(Term.total_hits if order == 'hits' else Term.term)

    sa = dict(session.query(SafeArticle.term, func.count(SafeArticle.title))
                     .group_by(SafeArticle.term))
    sp = dict(session.query(SafePhrase.term, func.count(SafePhrase.phrase))
                     .group_by(SafePhrase.term))

    return render_template('index.html', terms=q, sa=sa, sp=sp)

@bp.route("/new", methods=['GET', 'POST'])
def new_term():
    term = request.form.get('term')
    if request.method == 'POST' and term:
        q = 'insource:"{}"'.format(term)
        t = Term(term=term, total_hits=hit_count(q))
        session.add(t)
        session.commit()
        flash('new term added: {}'.format(term))
        return redirect(url_for('.index'))
    return render_template('new_term.html')

@bp.route("/mark_safe")
def mark_safe():
    title = request.args['title']
    term = request.args['term']
    offset = request.args.get('offset')

    t = Term.query.get(term)
    t.safe_articles.add(SafeArticle(title=title))
    session.commit()

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
    session.commit()
    flash('"{}" added as safe phrase for "{}"'.format(phrase, t.term))
    return redirect(url_for('.safe_phrases', term=term))

@bp.route("/remove_safe_article/<term>", methods=['POST'])
def remove_safe_article(term):
    term_clean = term.replace('_', ' ')
    t = Term.query.get(term_clean)
    article = request.form['item']
    sa = SafeArticle.query.filter_by(term=term_clean, title=article).one()
    session.delete(sa)
    session.commit()
    flash('"{}" is no longer a safe article for "{}"'.format(article, t.term))
    return redirect(url_for('.safe_articles', term=term))

@bp.route("/remove_safe_phrase/<term>", methods=['POST'])
def remove_safe_phrase(term):
    term_clean = term.replace('_', ' ')
    t = Term.query.get(term_clean)
    phrase = request.form['item']
    sp = SafePhrase.query.filter_by(term=term_clean, phrase=phrase).one()
    session.delete(sp)
    session.commit()
    flash('"{}" is no longer a safe phrase for "{}"'.format(phrase, t.term))
    return redirect(url_for('.safe_phrases', term=term))

@bp.route("/patrol/<term>")
def patrol(term):
    offset = int(request.args.get('offset') or 0)
    t = Term.query.get(term.replace('_', ' '))
    session.expire(t)

    safe_articles = {doc.title for doc in t.safe_articles}

    results = wiki_search(t.get_query(), offset=offset)
    if results.total_hits != t.total_hits:
        t.total_hits = results.total_hits
        session.commit()

    pattern = '|'.join(re.escape(safe.phrase) for safe in t.safe_phrases)
    re_phrase = re.compile('(' + pattern + ')', re.I)
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
