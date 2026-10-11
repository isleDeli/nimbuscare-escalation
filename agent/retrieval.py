import math
import re
from collections import Counter


def tokens(text):
    return re.findall(r'[a-z0-9]+', text.lower())


class Retriever:
    def __init__(self, articles):
        self.articles = articles
        self.counts = {key: Counter(tokens(a['title'] + ' ' + a['title'] + ' ' + a['text'])) for key, a in articles.items()}
        self.average = sum(map(lambda c: sum(c.values()), self.counts.values())) / max(1, len(articles))
        self.df = Counter(t for c in self.counts.values() for t in c)

    def search(self, query):
        scores = []
        for key, counts in self.counts.items():
            score = 0.0
            length = sum(counts.values())
            for term in set(tokens(query)):
                freq = counts[term]
                idf = math.log(1 + (len(self.counts) - self.df[term] + .5) / (self.df[term] + .5))
                score += idf * freq * 2.5 / (freq + 1.5 * (.25 + .75 * length / self.average))
            scores.append(dict(id=key, title=self.articles[key]['title'], score=round(score, 6)))
        return sorted(scores, key=lambda x: (-x['score'], x['id']))[:3]
