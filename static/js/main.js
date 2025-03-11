document.addEventListener('DOMContentLoaded', function() {
    const practiceInputs = document.querySelectorAll('.practice-input');
    const practiceForm = document.getElementById('practiceForm');
    const parentEmailForm = document.getElementById('parentEmailForm');
    const weekFilter = document.getElementById('weekFilter');
    const studentRecords = document.getElementById('studentRecords');
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    function calculateGrade(minutes) {
        let totalMinutes = 0;
        let practiceDays = 0;
        
        // Calculate total minutes and practice days
        Object.values(minutes).forEach(mins => {
            const minsInt = parseInt(mins);
            totalMinutes += minsInt;
            if (minsInt > 0) practiceDays++;
        });
        
        // Calculate base points based on total minutes
        let basePoints = 35; // Minimum points
        if (totalMinutes >= 100) basePoints = 80;
        else if (totalMinutes >= 90) basePoints = 75;
        else if (totalMinutes >= 80) basePoints = 70;
        else if (totalMinutes >= 70) basePoints = 65;
        else if (totalMinutes >= 60) basePoints = 60;
        else if (totalMinutes >= 50) basePoints = 55;
        else if (totalMinutes >= 40) basePoints = 50;
        else if (totalMinutes >= 30) basePoints = 45;
        else if (totalMinutes >= 20) basePoints = 40;
        
        // Add bonus points for 5+ practice days
        let bonusPoints = practiceDays >= 5 ? 5 : 0;
        
        return {
            grade: basePoints + bonusPoints,
            totalMinutes: totalMinutes,
            practiceDays: practiceDays,
            maxPossiblePoints: basePoints + bonusPoints + 20 // +20 for parent signature
        };
    }

    // Director Dashboard: Load weeks
    if (weekFilter) {
        fetch('/api/weeks')
            .then(response => response.json())
            .then(weeks => {
                weekFilter.innerHTML = weeks.map(week => 
                    `<option value="${week}">${new Date(week).toLocaleDateString()}</option>`
                ).join('');
                if (weeks.length > 0) {
                    loadWeekRecords(weeks[0]);
                }
            })
            .catch(error => console.error('Error loading weeks:', error));

        weekFilter.addEventListener('change', (e) => {
            loadWeekRecords(e.target.value);
        });
    }

    // Director Dashboard: Load records for selected week
    function loadWeekRecords(weekStart) {
        fetch(`/api/records/${weekStart}`)
            .then(response => response.json())
            .then(records => {
                studentRecords.innerHTML = records.map(record => {
                    const minutesObj = JSON.parse(record.minutes);
                    const { totalMinutes, practiceDays } = calculateGrade(minutesObj);
                    const signatureStatus = record.parent_signature_status === 'approved' ? 
                        '<span class="badge bg-success">Yes</span>' :
                        record.parent_signature_status === 'denied' ?
                        '<span class="badge bg-danger">Denied</span>' :
                        record.parent_signature_status === 'pending' ?
                        '<span class="badge bg-warning">Pending</span>' :
                        '<span class="badge bg-secondary">No</span>';
                    
                    return `
                        <tr>
                            <td>${record.student_name}</td>
                            <td>${record.instrument}</td>
                            <td>${totalMinutes}</td>
                            <td>${practiceDays}</td>
                            <td>${signatureStatus}</td>
                            <td>${record.total_points}/105</td>
                            <td>
                                <button class="btn btn-sm btn-info view-details" 
                                        data-minutes='${record.minutes}'
                                        data-comments='${record.comments || ""}'
                                        data-bs-toggle="modal"
                                        data-bs-target="#detailsModal">
                                    View Details
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');

                // Add event listeners to detail buttons
                document.querySelectorAll('.view-details').forEach(button => {
                    button.addEventListener('click', function() {
                        const minutes = JSON.parse(this.dataset.minutes);
                        const comments = this.dataset.comments;
                        
                        document.getElementById('detailsBody').innerHTML = Object.entries(minutes)
                            .map(([day, mins]) => `
                                <tr>
                                    <td>${day}</td>
                                    <td>${mins}</td>
                                </tr>
                            `).join('') + (
                                comments ? `
                                    <tr>
                                        <td colspan="2">
                                            <strong>Comments:</strong><br>
                                            ${comments}
                                        </td>
                                    </tr>
                                ` : ''
                            );
                    });
                });
            })
            .catch(error => console.error('Error loading records:', error));
    }

    // Student Dashboard: Handle practice inputs
    if (practiceInputs.length > 0) {
        practiceInputs.forEach(input => {
            input.addEventListener('input', updateTotals);
        });

        function updateTotals() {
            const minutes = {};
            practiceInputs.forEach(input => {
                minutes[input.dataset.day] = input.value || '0';
            });
            
            const { grade, totalMinutes, practiceDays, maxPossiblePoints } = calculateGrade(minutes);
            
            document.getElementById('totalMinutes').textContent = totalMinutes;
            document.getElementById('daysPracticed').textContent = practiceDays;
            document.getElementById('estimatedGrade').textContent = 
                `${grade}/85 (${maxPossiblePoints}/105 with parent signature)`;
        }

        // Initialize totals
        updateTotals();
    }

    // Student Dashboard: Handle practice form submission
    if (practiceForm) {
        practiceForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const minutes = {};
            const comments = {};
            
            practiceInputs.forEach(input => {
                minutes[input.dataset.day] = input.value || '0';
            });
            
            document.querySelectorAll('.comment-input').forEach(input => {
                comments[input.dataset.day] = input.value || '';
            });
            
            const weeklyComments = document.getElementById('weeklyComments').value;
            
            try {
                const response = await fetch('/api/practice', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        minutes: minutes,
                        comments: comments,
                        weeklyComments: weeklyComments
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (!data.parent_email) {
                        // Show parent email modal if not set
                        const modal = new bootstrap.Modal(document.getElementById('parentEmailModal'));
                        modal.show();
                    } else {
                        window.location.reload();
                    }
                } else {
                    throw new Error('Failed to save practice record');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error saving practice record. Please try again.');
            }
        });
    }

    // Handle parent email form submission
    if (parentEmailForm) {
        parentEmailForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const parentEmail = document.getElementById('parentEmail').value;
            
            try {
                const response = await fetch('/update_parent_email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        parent_email: parentEmail
                    })
                });
                
                if (response.ok) {
                    window.location.reload();
                } else {
                    throw new Error('Failed to update parent email');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error updating parent email. Please try again.');
            }
        });
    }
});
