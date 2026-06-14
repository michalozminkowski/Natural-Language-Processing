import os
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

from flask import Flask, request, jsonify, render_template
from rag_engine import rag_engine

app = Flask(__name__)

@app.route('/')
def index_route():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get("messages", [])
    current_state = data.get("state", {})
    
    if not messages:
        return jsonify({"error": "No messages provided."}), 400
        
    try:
        response_text, new_state = rag_engine.get_answer(messages, current_state)
        return jsonify({
            "response": response_text,
            "new_state": new_state
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
