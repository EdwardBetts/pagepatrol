from .database import session
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Base.query = session.query_property()

class SafePhrase(Base):
    __tablename__ = 'safe_phrase'
    phrase = Column(Unicode, primary_key=True)
    term = Column(Unicode, ForeignKey('term.term'), nullable=False)

class SafeArticle(Base):
    __tablename__ = 'safe_article'
    title = Column(Unicode, primary_key=True)
    term = Column(Unicode, ForeignKey('term.term'), primary_key=True)

class Term(Base):
    __tablename__ = 'term'
    term = Column(Unicode, primary_key=True)
    total_hits = Column(Integer())
    safe_phrases = relationship(SafePhrase, collection_class=set)
    safe_articles = relationship(SafeArticle, collection_class=set)

    def articles_with_safe_phrase(self):
        phrases = [x.phrase for x in self.safe_phrases]

        titles = set()
        for phrase in phrases:
            q = (session.query(func.max(SearchResult.timestamp))
                        .filter(SearchResult.q == phrase))
            most_recent = q.one()[0]

            safe = SearchResult.query.filter(SearchResult.q == phrase,
                                             SearchResult.timestamp == most_recent)

            titles.update(doc.title for doc in safe)
        return titles

    def get_query(self):
        safe_phrases = ''.join(' -insource:"{}"'.format(safe.phrase) for safe in self.safe_phrases)
        q = 'insource:"{}"'.format(self.term)
        if len(q) + len(safe_phrases) <= 300:
            q += safe_phrases
        return q

class SearchResult(Base):
    __tablename__ = 'search_result'
    q = Column(Unicode, primary_key=True)
    title = Column(Unicode, primary_key=True)
    timestamp = Column(DateTime(), primary_key=True)
