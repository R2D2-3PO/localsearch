import json
import os
from flask import Flask, render_template, request, jsonify
from elasticsearch import Elasticsearch, helpers
import nltk
from nltk.corpus import wordnet

# Initialize Flask app and Elasticsearch client s
app = Flask(__name__)
es = Elasticsearch(['http://localhost:9200'])

# Download required NLTK data
try:
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
except Exception as e:
    print(f"Error downloading NLTK data: {e}")


# Index JSON data into Elasticsearch
def index_json_data():
    # Check if index already exists
    if es.indices.exists(index='files'):
        print("Index 'files' already exists, skipping indexing.")
        return

    # Verify JSON file exists
    json_file = 'files.json'
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found in project directory.")
        return

    try:
        # Load JSON data
        with open(json_file, 'r') as f:
            data = json.load(f)

        if not data:
            print("Error: JSON file is empty.")
            return

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
        print(f"Indexed {len(actions)} documents successfully!")
    except Exception as e:
        print(f"Error indexing data: {e}")


# Get synonyms for a word using WordNet
def get_synonyms(word):
    synonyms = set()
    try:
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                synonyms.add(lemma.name().lower())
    except Exception as e:
        print(f"Error fetching synonyms for '{word}': {e}")
    return list(synonyms) or [word]  # Return original word if no synonyms


# Flask routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '').lower()
    if not query:
        return jsonify({'error': 'Query is empty'}), 400

    words = query.split()
    print(f"Processing query: {query}")

    # Get synonyms for each word
    all_terms = []
    for word in words:
        synonyms = get_synonyms(word)
        print(f"Word: {word}, Synonyms: {synonyms}")
        all_terms.append({
            'terms': [word] + synonyms
        })

    # Build Elasticsearch query
    es_query = {
        'query': {
            'bool': {
                'should': [
                    {
                        'multi_match': {
                            'query': term['terms'][0],
                            'fields': ['file_name^2', 'ftp_path'],
                            'fuzziness': 'AUTO'
                        }
                    } for term in all_terms
                ],
                'minimum_should_match': 1
            }
        }
    }

    # Execute search
    try:
        results = es.search(index='files', body=es_query, size=100)
        hits = results['hits']['hits']
        print(f"Found {len(hits)} results")

        # Format results
        formatted_results = [
            {
                'file_name': hit['_source']['file_name'],
                'ftp_path': hit['_source']['ftp_path'],
                'size': hit['_source']['size'],
                'modified': hit['_source']['modified'],
                'score': hit['_score']
            }
            for hit in hits
        ]
        return jsonify(formatted_results)
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500


# Run indexing on startup
if __name__ == '__main__':
    if not es.ping():
        print("Error: Elasticsearch is not running on localhost:9200")
    else:
        index_json_data()
        app.run(debug=True)