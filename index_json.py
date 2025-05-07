import json
from elasticsearch import Elasticsearch, helpers
import nltk
from nltk.corpus import wordnet

# Download WordNet data (run once)
nltk.download('wordnet')

# Initialize Elasticsearch client
es = Elasticsearch(['http://localhost:9200'])

# Load JSON data
with open('audio_cache.json', 'r') as f:
    data = json.load(f)

# Prepare data for bulk indexing
actions = [
    {
        '_index': 'files',
        '_id': idx,
        '_source': {
            'file_name': item['file_name'],
            'ftp_path': item['ftp_path'],
            'size': item['size'],
            'modified': item['modified']
        }
    }
    for idx, (path, item) in enumerate(data.items())
]

# Bulk index the data
helpers.bulk(es, actions)
print("Data indexed successfully!")