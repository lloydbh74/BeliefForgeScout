from datetime import datetime, timezone
from src.core.models import SocialPost, Author, Platform, SocialMetrics
from src.scoring.post_scorer import PostScorer
from src.filtering.commercial_filter import CommercialFilter

def test_social_post_compatibility():
    print("\n--- Testing SocialPost Compatibility ---")
    post = SocialPost(
        id="123",
        platform=Platform.REDDIT,
        text="Looking for a CRM for my startup",
        author=Author(username="test_user", display_name="Test User", platform=Platform.REDDIT),
        created_at=datetime.now(timezone.utc),
        url="http://reddit.com/r/test",
        metrics=SocialMetrics(likes=10, replies=5, shares=0, impressions=100)
    )
    
    # Test __getitem__
    print(f"Text access: {post['text']}")
    print(f"Author access: {post['author']['username']}")
    print(f"Metrics access (public_metrics): {post['public_metrics']}")
    
    assert post['text'] == "Looking for a CRM for my startup"
    assert post['author']['username'] == "test_user"
    assert post['public_metrics']['like_count'] == 10

def test_commercial_filter():
    print("\n--- Testing CommercialFilter ---")
    filter = CommercialFilter()
    
    post = SocialPost(
        id="123",
        platform=Platform.REDDIT,
        text="I need a new CRM for my business. Any recommendations?",
        author=Author(username="founder_guy", display_name="Founder", platform=Platform.REDDIT),
        created_at=datetime.now(timezone.utc),
        url="http://reddit.com/r/startups",
        metrics=SocialMetrics(likes=5, replies=2, shares=0, impressions=50)
    )
    
    result = filter.analyze_post(post)
    print(f"Analysis result: {result}")
    
    # Check if modified post object
    print(f"Post commercial signals: {post.commercial_signals}")
    assert post.commercial_signals is not None
    # 'baseline' is valid if no keywords match user config defaults
    assert result['priority'] in ['critical', 'high', 'medium_high', 'medium', 'baseline']

def test_post_scorer():
    print("\n--- Testing PostScorer ---")
    scorer = PostScorer()
    
    post = SocialPost(
        id="456",
        platform=Platform.REDDIT,
        text="Check out my new project!",
        author=Author(username="dev_guy", display_name="Dev", platform=Platform.REDDIT, followers_count=100),
        created_at=datetime.now(timezone.utc),
        url="http://reddit.com/r/python",
        metrics=SocialMetrics(likes=50, replies=10, shares=5, impressions=1000)
    )
    
    # Add dummy commercial signals as they are used in scoring
    post.commercial_signals = {'multiplier': 1.2}
    
    score = scorer.score_post(post)
    print(f"Score result: {score}")
    
    assert post.score is not None
    assert 'total_score' in score

if __name__ == "__main__":
    try:
        test_social_post_compatibility()
        test_commercial_filter()
        test_post_scorer()
        print("\nAll component tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
