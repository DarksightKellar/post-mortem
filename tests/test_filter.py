from reddit_automation.pipeline.filter import filter_candidates


def test_filter_candidates_rejects_candidate_with_banned_term():
    config = {
        'filters': {
            'exclude_categories': ['nsfw'],
            'exclude_low_context': True,
            'dedupe_similar_posts': True,
        }
    }
    raw = [
        {
            'candidate_id': '1',
            'subreddit': 'tifu',
            'title': 'This turned into porn somehow',
            'body': '',
            'top_comments': [],
        }
    ]
    assert filter_candidates(raw, config) == []
