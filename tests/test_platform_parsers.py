"""Facebook and Threads HTML parser tests."""

from crawlers.facebook.parser import parse_comments_from_html as parse_fb
from crawlers.threads.parser import parse_comments_from_html as parse_th


def test_facebook_parser_json_blob():
    html = '''
    "body":{"text":"Tu bahar aa kabhi"},"name":"troll_user_99"
    '''
    comments = parse_fb(html, target_username="influencer", post_url="https://facebook.com/influencer")
    assert len(comments) >= 1
    assert comments[0].platform == "facebook"


def test_threads_parser():
    html = '"text":"Fake influencer thread","username":"hater_12"'
    comments = parse_th(html, target_username="star", post_url="https://www.threads.net/@star")
    assert len(comments) >= 1
    assert comments[0].accused_username == "hater_12"
