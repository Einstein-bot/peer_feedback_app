from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import uuid

# Create Flask app
app = Flask(__name__)

# Initialize CORS to allow cross-origin requests
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app)

# Temporary storage for the participants and feedback for MVP purposes
participants = []
feedback_data = {}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin_dashboard():
    session_id = None
    session_link = None
    if 'session_id' in request.args:
        session_id = request.args.get('session_id')
        session_link = url_for('feedback_session', session_id=session_id, participant=participants[0], _external=True)

    return render_template('admin.html', participants=participants, session_link=session_link, session_id=session_id)

@app.route('/add_participants', methods=['POST'])
def add_participants():
    new_participants = request.form.get('participants')
    if new_participants:
        participants.extend([p.strip() for p in new_participants.split(',')])
    return redirect(url_for('admin_dashboard'))

@app.route('/start_poll')
def start_poll():
    if participants:
        # Generate a unique session ID to identify the feedback session
        session_id = str(uuid.uuid4())
        # Redirect the admin back to the admin page, including the session ID as a parameter
        return redirect(url_for('admin_dashboard', session_id=session_id))
    return redirect(url_for('admin_dashboard'))

@app.route('/feedback/<session_id>/<participant>', methods=['GET', 'POST'])
def feedback_session(session_id, participant):
    if request.method == 'POST':
        feedback = {
            'Communicate': request.form.get('communicate'),
            'Hustle': request.form.get('hustle'),
            'Ownership': request.form.get('ownership'),
            'Improve': request.form.get('improve'),
            'Conscientious': request.form.get('conscientious'),
            'Attitudes': request.form.get('attitudes'),
            'Support': request.form.get('support'),
            'Get It': 'Yes' if request.form.get('get_it') else 'No',
            'Want It': 'Yes' if request.form.get('want_it') else 'No',
            'Capacity': 'Yes' if request.form.get('capacity') else 'No'
        }

        # Store feedback with session_id as the key
        if session_id not in feedback_data:
            feedback_data[session_id] = {}
        if participant not in feedback_data[session_id]:
            feedback_data[session_id][participant] = []
        feedback_data[session_id][participant].append(feedback)

        # Emit the feedback to a specific room (admin view)
        socketio.emit('new_feedback', {'participant': participant, 'feedback': feedback}, room=session_id)

        # Proceed to the next participant if available
        next_index = participants.index(participant) + 1
        if next_index < len(participants):
            return redirect(url_for('feedback_session', session_id=session_id, participant=participants[next_index]))
        else:
            return redirect(url_for('success'))

    return render_template('feedback.html', participant=participant)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/results/<session_id>')
def results(session_id):
    # Aggregate results for each participant
    aggregated_feedback = {}
    if session_id in feedback_data:
        for participant, feedback_list in feedback_data[session_id].items():
            aggregated_feedback[participant] = {
                'Communicate': sum([f['Communicate'] == '+' for f in feedback_list]),
                'Hustle': sum([f['Hustle'] == '+' for f in feedback_list]),
                # Add other aggregated feedback metrics here...
            }

    return render_template('results.html', feedback_data=aggregated_feedback, session_id=session_id)

@app.route('/export/<session_id>')
def export_results(session_id):
    # Exporting to a simple CSV for MVP purposes
    output = "Participant,Communicate,Hustle,Ownership,Improve,Conscientious,Attitudes,Support,Get It,Want It,Capacity\n"
    if session_id in feedback_data:
        for participant, feedback_list in feedback_data[session_id].items():
            for feedback in feedback_list:
                output += f"{participant},{feedback['Communicate']},{feedback['Hustle']},{feedback['Ownership']},{feedback['Improve']},{feedback['Conscientious']},{feedback['Attitudes']},{feedback['Support']},{feedback['Get It']},{feedback['Want It']},{feedback['Capacity']}\n"

    response = app.response_class(
        response=output,
        status=200,
        mimetype='text/csv'
    )
    response.headers["Content-Disposition"] = "attachment; filename=results.csv"
    return response

# Event handler for participants joining a session
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'msg': f'{data["username"]} has joined the session.'}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)

