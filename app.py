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
current_session_id = None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin_dashboard():
    session_link = None
    if current_session_id:
        session_link = url_for('feedback_session', session_id=current_session_id, participant=participants[0], _external=True)

    return render_template('admin.html', participants=participants, session_link=session_link, session_id=current_session_id)

@app.route('/add_participants', methods=['POST'])
def add_participants():
    new_participants = request.form.get('participants')
    if new_participants:
        participants.extend([p.strip() for p in new_participants.split(',')])
    return redirect(url_for('admin_dashboard'))

@app.route('/start_poll')
def start_poll():
    global current_session_id
    if participants:
        # Generate a unique session ID to identify the feedback session
        current_session_id = str(uuid.uuid4())
        # Redirect the admin back to the admin page, including the session ID as a parameter
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_dashboard'))

@app.route('/feedback/<session_id>/<participant>', methods=['GET', 'POST'])
def feedback_session(session_id, participant):
    # Debugging print statements
    print(f"Session ID: {session_id}")
    print(f"Participant: {participant}")

    if request.method == 'POST':
        # Convert the ratings to numerical scores
        def convert_rating(value):
            if value == '+':
                return 10
            elif value == '+/-':
                return 5
            elif value == '-':
                return 0
            return None

        feedback = {
            'Communicate clearly, professionally, and with kindness.': convert_rating(request.form.get('Communicate clearly, professionally, and with kindness.')),
            'Hustle but don\'t rush.': convert_rating(request.form.get('Hustle but don\'t rush.')),
            'Ownership over results.': convert_rating(request.form.get('Ownership over results.')),
            'Improve everyday with enthusiasm.': convert_rating(request.form.get('Improve everyday with enthusiasm.')),
            'Conscientious attention to detail.': convert_rating(request.form.get('Conscientious attention to detail.')),
            'Elevate attitudes and have fun.': convert_rating(request.form.get('Elevate attitudes and have fun.')),
            'Support one another generously.': convert_rating(request.form.get('Support one another generously.')),
            'Get It': 10 if request.form.get('get_it') == 'yes' else 0,
            'Want It': 10 if request.form.get('want_it') == 'yes' else 0,
            'Capacity': 10 if request.form.get('capacity') == 'yes' else 0
        }

        print(f"Received feedback: {feedback}")

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

    core_values = [
        "Communicate clearly, professionally, and with kindness.",
        "Hustle but don't rush.",
        "Ownership over results.",
        "Improve everyday with enthusiasm.",
        "Conscientious attention to detail.",
        "Elevate attitudes and have fun.",
        "Support one another generously."
    ]
    return render_template('feedback.html', core_values=core_values, participant=participant, session_id=session_id)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/results/<session_id>')
def results(session_id):
    # Aggregate results for each participant
    aggregated_feedback = {}
    if session_id in feedback_data:
        for participant, feedback_list in feedback_data[session_id].items():
            num_feedbacks = len(feedback_list)
            core_value_keys = [
                'Communicate clearly, professionally, and with kindness.',
                'Hustle but don\'t rush.',
                'Ownership over results.',
                'Improve everyday with enthusiasm.',
                'Conscientious attention to detail.',
                'Elevate attitudes and have fun.',
                'Support one another generously.'
            ]
            get_want_capacity_keys = ['Get It', 'Want It', 'Capacity']

            # Calculate average for core values
            core_values_avg = {
                key: sum([f[key] for f in feedback_list]) / num_feedbacks if num_feedbacks > 0 else 0
                for key in core_value_keys
            }

            # Calculate average for Get It, Want It, Capacity
            get_want_capacity_avg = {
                key: sum([f[key] for f in feedback_list]) / num_feedbacks if num_feedbacks > 0 else 0
                for key in get_want_capacity_keys
            }

            # Calculate overall score by averaging all averages
            all_averages = list(core_values_avg.values()) + list(get_want_capacity_avg.values())
            overall_score = sum(all_averages) / len(all_averages) if len(all_averages) > 0 else 0

            # Combine all averages into aggregated feedback
            aggregated_feedback[participant] = {
                **core_values_avg,
                **get_want_capacity_avg,
                'Overall Score': overall_score
            }

    # Debugging print statement to see the data being passed to the template
    print(f"Aggregated Feedback: {aggregated_feedback}")

    return render_template('results.html', feedback_data=aggregated_feedback, session_id=session_id)

@app.route('/export/<session_id>')
def export_results(session_id):
    # Exporting to a simple CSV for MVP purposes
    output = "Participant,Communicate,Hustle,Ownership,Improve,Conscientious,Attitudes,Support,Get It,Want It,Capacity,Overall Score\n"
    if session_id in feedback_data:
        for participant, feedback_list in feedback_data[session_id].items():
            num_feedbacks = len(feedback_list)
            if num_feedbacks > 0:
                core_values_avg = {
                    key: sum([f[key] for f in feedback_list]) / num_feedbacks for key in [
                        'Communicate clearly, professionally, and with kindness.',
                        'Hustle but don\'t rush.',
                        'Ownership over results.',
                        'Improve everyday with enthusiasm.',
                        'Conscientious attention to detail.',
                        'Elevate attitudes and have fun.',
                        'Support one another generously.'
                    ]
                }
                get_want_capacity_avg = {
                    key: sum([f[key] for f in feedback_list]) / num_feedbacks for key in ['Get It', 'Want It', 'Capacity']
                }
                all_averages = list(core_values_avg.values()) + list(get_want_capacity_avg.values())
                overall_score = sum(all_averages) / len(all_averages)

                output += f"{participant},{core_values_avg['Communicate clearly, professionally, and with kindness.']},{core_values_avg['Hustle but don\'t rush.']},{core_values_avg['Ownership over results.']},{core_values_avg['Improve everyday with enthusiasm.']},{core_values_avg['Conscientious attention to detail.']},{core_values_avg['Elevate attitudes and have fun.']},{core_values_avg['Support one another generously.']},{get_want_capacity_avg['Get It']},{get_want_capacity_avg['Want It']},{get_want_capacity_avg['Capacity']},{overall_score}\n"

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