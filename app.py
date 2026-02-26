from flask import Flask, jsonify, render_template, request
import json
import random
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from analytics import Analytics

load_dotenv()

app = Flask(__name__)
analytics = Analytics()

# OpenAI client configured for OpenRouter
api_key = os.getenv('OPENROUTER_API_KEY')
endpoint = "https://openrouter.ai/api/v1"
chat_client = OpenAI(api_key=api_key, base_url=endpoint)

# ChromaDB setup
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="jokes")

def load_jokes():
    """Load jokes from the JSON file."""
    try:
        with open('jokes.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def format_joke(joke):
    """Format a joke for display."""
    if joke.get('type') == 'single':
        return joke.get('joke', '')
    elif joke.get('type') == 'twopart':
        return f"{joke.get('setup', '')} {joke.get('delivery', '')}"
    return str(joke)

def initialize_chroma():
    """Initialize ChromaDB with jokes if not already done."""
    jokes = load_jokes()
    
    # Check if collection is empty
    if collection.count() == 0 and jokes:
        print("Initializing ChromaDB with jokes...")
        
        documents = []
        metadatas = []
        ids = []
        
        for i, joke in enumerate(jokes):
            joke_text = format_joke(joke)
            documents.append(joke_text)
            metadatas.append({
                'category': joke.get('category', 'Unknown'),
                'type': joke.get('type', 'unknown'),
                'id': str(joke.get('id', i))
            })
            ids.append(f"joke_{i}")
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Added {len(documents)} jokes to ChromaDB")

def search_jokes_by_query(query, n_results=3):
    """Search for relevant jokes using ChromaDB."""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    return results

@app.route('/')
def home():
    """Serve the home page."""
    return render_template('index.html')

@app.route('/api/joke')
def get_random_joke():
    """Get a random joke from the collection."""
    jokes = load_jokes()
    
    if not jokes:
        return jsonify({'error': 'No jokes available'}), 404
    
    joke = random.choice(jokes)
    return jsonify(joke)

@app.route('/api/jokes')
def get_all_jokes():
    """Get all jokes."""
    jokes = load_jokes()
    return jsonify({'jokes': jokes, 'count': len(jokes)})

@app.route('/api/ask', methods=['POST'])
def ask_ai():
    """Ask AI to find jokes based on user request using RAG with ChromaDB."""
    data = request.json
    user_message = data.get('message', '')
    start_time = time.time()
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Check for NSFW/inappropriate requests
        nsfw_keywords = ['nsfw', 'inappropriate', 'explicit', 'adult', 'dirty', 'sexual']
        if any(keyword in user_message.lower() for keyword in nsfw_keywords):
            response_time = (time.time() - start_time) * 1000
            analytics.log_query(user_message, 'nsfw_blocked', 0, response_time)
            
            return jsonify({
                'response': "I cannot provide NSFW or inappropriate content. All jokes in my collection are filtered to exclude such content.",
                'jokes': []
            })
        
        # Load all jokes for counting and analysis
        all_jokes = load_jokes()
        
        if not all_jokes:
            return jsonify({'error': 'No jokes available in the collection'}), 500
        
        # Check if this is a counting question
        if 'how many' in user_message.lower() or 'count' in user_message.lower():
            try:
                # Search for relevant jokes
                search_results = search_jokes_by_query(user_message, n_results=len(all_jokes))
                
                # Extract category or topic from the question
                prompt_count = f"""Analyze this question: "{user_message}"

The user is asking about the count of jokes in a specific category or topic.
Based on the question, what category or topic are they asking about?
Return ONLY the category/topic name (e.g., "physics", "programming", "christmas", "misc").
If unclear, return "unknown"."""

                response = chat_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt_count}],
                    timeout=10
                )
                
                # Check if response is valid
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty response from AI model")
                
                topic = response.choices[0].message.content.strip().lower()
                
            except Exception as llm_error:
                # Fallback: Use simple keyword extraction if LLM fails
                import re
                match = re.search(r'how many (\w+)', user_message.lower())
                topic = match.group(1) if match else 'unknown'
                print(f"LLM failed for counting, using fallback: {llm_error}")
            
            # Count jokes matching the topic
            count = 0
            matching_jokes = []
            
            for joke in all_jokes:
                joke_category = joke.get('category', '').lower()
                joke_text = format_joke(joke).lower()
                
                if topic in joke_category or topic in joke_text:
                    count += 1
                    matching_jokes.append(joke)
            
            if count > 0:
                response_time = (time.time() - start_time) * 1000
                analytics.log_query(user_message, 'success', len(matching_jokes[:3]), response_time)
                
                return jsonify({
                    'response': f"I have {count} {topic} joke{'s' if count != 1 else ''} in my collection.",
                    'jokes': matching_jokes[:3]  # Show first 3 as examples
                })
            else:
                response_time = (time.time() - start_time) * 1000
                analytics.log_query(user_message, 'no_results', 0, response_time)
                
                return jsonify({
                    'response': f"I have 0 {topic} jokes in my collection.",
                    'jokes': []
                })
        
        # Check if this is a yes/no question about existence
        if user_message.strip().endswith('?') and any(word in user_message.lower() for word in ['are there', 'do you have', 'is there', 'any']):
            try:
                # Search for relevant jokes
                search_results = search_jokes_by_query(user_message, n_results=10)
                
                if search_results['documents'][0]:
                    # Get matching jokes
                    matching_jokes = []
                    for doc in search_results['documents'][0][:5]:
                        for joke in all_jokes:
                            if format_joke(joke) == doc:
                                matching_jokes.append(joke)
                                break
                    
                    if matching_jokes:
                        return jsonify({
                            'response': f"Yes, I found {len(matching_jokes)} joke{'s' if len(matching_jokes) != 1 else ''} matching your query. Here are some examples:",
                            'jokes': matching_jokes[:3]
                        })
                
                return jsonify({
                    'response': "No, I don't have any jokes matching that description in my collection.",
                    'jokes': []
                })
            except Exception as search_error:
                print(f"ChromaDB search failed: {search_error}")
                return jsonify({
                    'response': "I'm having trouble searching the joke collection. Please try again.",
                    'jokes': []
                })
        
        # Regular joke request - search and recommend
        try:
            search_results = search_jokes_by_query(user_message, n_results=5)
            
            if not search_results['documents'][0]:
                response_time = (time.time() - start_time) * 1000
                analytics.log_query(user_message, 'no_results', 0, response_time)
                
                return jsonify({
                    'response': "I couldn't find any jokes matching your request.",
                    'jokes': []
                })
            
            # Get the relevant jokes
            relevant_jokes_text = "\n\n".join([
                f"Joke {i+1}: {doc}" 
                for i, doc in enumerate(search_results['documents'][0])
            ])
            
            # Create prompt for the LLM
            prompt = f"""You are a helpful assistant that recommends jokes based on user requests.

User request: {user_message}

Here are some relevant jokes from the collection:
{relevant_jokes_text}

Based on the user's request, select the joke number(s) that best match what they're asking for.
Return ONLY the joke number(s) separated by commas (e.g., "1" or "1,3,5").
If none match well, return "none"."""

            # Call OpenRouter with GPT-4o-mini
            response = chat_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=10
            )
            
            # Validate response
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from AI model")
            
            selected = response.choices[0].message.content.strip()
            
            if selected.lower() == 'none':
                response_time = (time.time() - start_time) * 1000
                analytics.log_query(user_message, 'no_results', 0, response_time)
                
                return jsonify({
                    'response': "I couldn't find a joke that matches your request perfectly. Would you like a random joke instead?",
                    'jokes': []
                })
            
            # Parse selected joke numbers and map back to original jokes
            joke_indices = [int(num.strip()) - 1 for num in selected.split(',') if num.strip().isdigit()]
            
            # Get the actual joke objects from the search results
            selected_jokes = []
            
            for idx in joke_indices:
                if 0 <= idx < len(search_results['documents'][0]):
                    # Find the joke in our collection by matching the text
                    joke_text = search_results['documents'][0][idx]
                    for joke in all_jokes:
                        if format_joke(joke) == joke_text:
                            selected_jokes.append(joke)
                            break
            
            # Fallback if no jokes were selected
            if not selected_jokes and search_results['documents'][0]:
                # Return the first result from ChromaDB as fallback
                first_doc = search_results['documents'][0][0]
                for joke in all_jokes:
                    if format_joke(joke) == first_doc:
                        selected_jokes.append(joke)
                        break
            
            response_time = (time.time() - start_time) * 1000
            analytics.log_query(user_message, 'success', len(selected_jokes), response_time)
            
            return jsonify({
                'response': "Here's what I found for you:",
                'jokes': selected_jokes
            })
            
        except Exception as llm_error:
            # Fallback: Return top ChromaDB results without LLM selection
            print(f"LLM selection failed, using ChromaDB results directly: {llm_error}")
            analytics.log_llm_failure('llm_selection_error', str(llm_error), 'chromadb_direct')
            
            try:
                search_results = search_jokes_by_query(user_message, n_results=3)
                fallback_jokes = []
                
                for doc in search_results['documents'][0]:
                    for joke in all_jokes:
                        if format_joke(joke) == doc:
                            fallback_jokes.append(joke)
                            break
                
                response_time = (time.time() - start_time) * 1000
                analytics.log_query(user_message, 'success', len(fallback_jokes), response_time)
                
                return jsonify({
                    'response': "Here's what I found for you:",
                    'jokes': fallback_jokes
                })
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                response_time = (time.time() - start_time) * 1000
                analytics.log_query(user_message, 'error', 0, response_time, str(fallback_error))
                
                return jsonify({
                    'response': "I'm having trouble processing your request. Here's a random joke instead:",
                    'jokes': [random.choice(all_jokes)] if all_jokes else []
                })
        
    except Exception as e:
        print(f"Unexpected error in /api/ask: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback on a response."""
    data = request.json
    query_id = data.get('query_id')
    rating = data.get('rating')  # 1-5 or thumbs up/down
    comment = data.get('comment', '')
    
    if not rating:
        return jsonify({'error': 'Rating is required'}), 400
    
    analytics.log_feedback(query_id, rating, comment)
    
    return jsonify({'success': True, 'message': 'Thank you for your feedback!'})

@app.route('/api/analytics/stats')
def get_analytics_stats():
    """Get analytics statistics (admin endpoint)."""
    stats = analytics.get_stats()
    return jsonify(stats)

@app.route('/api/analytics/failed-queries')
def get_failed_queries():
    """Get recent failed queries (admin endpoint)."""
    failed = analytics.get_failed_queries(limit=20)
    return jsonify({'failed_queries': failed})

@app.route('/api/analytics/low-satisfaction')
def get_low_satisfaction():
    """Get queries with low user satisfaction (admin endpoint)."""
    low_rated = analytics.get_low_satisfaction_queries(threshold=2, limit=20)
    return jsonify({'low_satisfaction_queries': low_rated})

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard for monitoring."""
    return render_template('admin_dashboard.html')

if __name__ == '__main__':
    # Initialize ChromaDB on startup
    initialize_chroma()
    app.run(debug=True)
