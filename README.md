# Band Practice Journal

An interactive web-based application for middle school band students to track their practice time and receive grades based on their practice minutes and parent verification.

## Features

- Students can log daily practice minutes
- Real-time grade calculation based on:
  - Total minutes practiced per week
  - Number of practice days
  - Parent signature verification
- Parent dashboard to review and sign practice logs
- Band director dashboard to view all student records and grades

## Grade Calculation

The final grade (out of 105 points) is calculated as follows:

- Base grade based on total minutes:
  - 100+ minutes: 80 points
  - 90-99 minutes: 75 points
  - 80-89 minutes: 70 points
  - 70-79 minutes: 65 points
  - 60-69 minutes: 60 points
  - 50-59 minutes: 55 points
  - 40-49 minutes: 50 points
  - 30-39 minutes: 45 points
  - 20-29 minutes: 40 points
  - 0-19 minutes: 35 points
- Parent signature: +20 points
- Practice 5+ days in a week: +5 bonus points

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python app.py
```

3. Access the application at http://localhost:5000

## User Types

1. Students
   - Can log daily practice minutes
   - View their current grade
   - Track progress over time

2. Parents
   - View their child's practice logs
   - Digitally sign weekly practice records
   - Monitor practice habits

3. Band Director
   - View all student records
   - Monitor class progress
   - Access detailed practice information
   - View final grades including parent signatures
