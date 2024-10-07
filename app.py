from flask import Flask, render_template, request, redirect, url_for, jsonify
import os

app = Flask(__name__)

# Temporary storage for the participants and feedback for MVP purposes
participants = []
feedback_data = {}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin.html', participants=participants)

@app.route('/add_participants', methods=['POST'])
def add_participants():
    new_participants = request.form.get('participants')
    if new_participants:
        participants.extend([p.strip() for p in new_participants.split(',')])
    return redirect(url_for('admin_dashboard'))

@app.route('/start_poll')
def start_poll():
    if participants:
        return redirect(url_for('feedback', participant=participants[0]))
    return redirect(url_for('admin_dashboard'))

@app.route('/feedback/<participant>', methods=['GET', 'POST'])
def feedback(participant):
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
        feedback_data[participant] = feedback

        # Proceed to the next participant if available
        next_index = participants.index(participant) + 1
        if next_index < len(participants):
            return redirect(url_for('feedback', participant=participants[next_index]))
        else:
            return redirect(url_for('results'))

    return render_template('feedback.html', participant=participant)

@app.route('/results')
def results():
    return render_template('results.html', feedback_data=feedback_data)

@app.route('/export')
def export_results():
    # Exporting to a simple CSV for MVP purposes
    output = "Participant,Communicate,Hustle,Ownership,Improve,Conscientious,Attitudes,Support,Get It,Want It,Capacity\n"
    for participant, feedback in feedback_data.items():
        output += f"{participant},{feedback['Communicate']},{feedback['Hustle']},{feedback['Ownership']},{feedback['Improve']},{feedback['Conscientious']},{feedback['Attitudes']},{feedback['Support']},{feedback['Get It']},{feedback['Want It']},{feedback['Capacity']}\n"
    
    response = app.response_class(
        response=output,
        status=200,
        mimetype='text/csv'
    )
    response.headers["Content-Disposition"] = "attachment; filename=results.csv"
    return response

if __name__ == '__main__':
    app.run(debug=True)
