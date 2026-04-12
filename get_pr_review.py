import urllib.request
import json
import sys

url = "https://api.github.com/repos/BharathASL/four-wheeler-edge-brain/pulls/26/reviews/4094423508/comments"

req = urllib.request.Request(url, headers={
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'python-urllib'
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        for comment in data:
            print(f"File: {comment['path']}")
            print(f"Line: {comment.get('line')}")
            print(f"Body: {comment['body']}")
            print("-" * 40)
except Exception as e:
    print(f"Error: {e}")
