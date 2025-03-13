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
                        '<span class="badge bg-success">Yes (+20 pts)</span>' :
                        record.parent_signature_status === 'denied' ?
                        '<span class="badge bg-danger">Denied</span>' :
                        record.parent_signature_status === 'pending' ?
                        '<span class="badge bg-warning text-dark">Pending</span>' :
                        '<span class="badge bg-secondary">No</span>';
                    
                    return `
                        <tr>
                            <td>${record.last_name}</td>
                            <td>${record.first_name}</td>
                            <td>${record.instrument}</td>
                            <td>${totalMinutes}</td>
                            <td>
                                ${practiceDays}
                                ${practiceDays >= 5 ? '<span class="badge bg-success">+5 pts</span>' : ''}
                            </td>
                            <td>${signatureStatus}</td>
                            <td>${record.total_points}/105</td>
                            <td>
                                <button class="btn btn-sm btn-primary view-details" 
                                        data-minutes='${record.minutes}'
                                        data-comments='${record.daily_comments || "{}"}'
                                        data-first-name="${record.first_name}"
                                        data-last-name="${record.last_name}"
                                        data-bs-toggle="modal"
                                        data-bs-target="#detailsModal">
                                    View Details
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            })
            .catch(error => console.error('Error loading records:', error));
    }

    // Student Dashboard: Handle daily practice saving
    document.querySelectorAll('.save-daily, .edit-day').forEach(button => {
        button.addEventListener('click', async function() {
            const day = this.dataset.day;
            const minutesInput = document.querySelector(`.practice-input[data-day="${day}"]`);
            const commentInput = document.querySelector(`.comment-input[data-day="${day}"]`);
            
            // If this is an edit button, enable the inputs and change button
            if (this.classList.contains('edit-day')) {
                minutesInput.disabled = false;
                commentInput.disabled = false;
                this.classList.remove('btn-outline-secondary', 'edit-day');
                this.classList.add('btn-primary', 'save-daily');
                this.textContent = 'Save';
                return;
            }
            
            const data = {
                day: day,
                minutes: parseInt(minutesInput.value) || 0,
                comment: commentInput.value || ''
            };
            
            try {
                const response = await fetch('/api/practice/daily', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    const responseData = await response.json();
                    
                    // Show success message
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-success alert-dismissible fade show';
                    alertDiv.innerHTML = `
                        Practice saved for ${day}!
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.querySelector('.card-body').insertBefore(
                        alertDiv,
                        document.querySelector('.table-responsive')
                    );
                    
                    // Update streak if available
                    if (responseData.streak && document.getElementById('streakCount')) {
                        document.getElementById('streakCount').textContent = responseData.streak;
                    }
                    
                    // Disable inputs after saving
                    minutesInput.disabled = true;
                    commentInput.disabled = true;
                    
                    // Convert save button back to edit button for past days
                    if (this.textContent === 'Save') {
                        this.classList.remove('btn-primary', 'save-daily');
                        this.classList.add('btn-outline-secondary', 'edit-day');
                        this.textContent = 'Edit';
                    } else {
                        this.disabled = true;
                        this.textContent = 'Saved!';
                    }
                    
                    // Update totals
                    updateTotals();
                    
                    // Show parent email modal if not set
                    if (!responseData.parent_email) {
                        const modal = new bootstrap.Modal(document.getElementById('parentEmailModal'));
                        modal.show();
                    }
                } else {
                    throw new Error('Failed to save practice');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error saving practice. Please try again.');
            }
        });
    });

    // Student Dashboard: Handle weekly practice submission
    document.getElementById('submitWeek')?.addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('weeklyCommentsModal'));
        modal.show();
    });

    document.getElementById('confirmSubmit')?.addEventListener('click', async function() {
        const comments = document.getElementById('weeklyComments').value;
        
        try {
            const response = await fetch('/api/practice/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ comments: comments })
            });
            
            if (response.ok) {
                // Reload page to show updated status
                window.location.reload();
            } else {
                throw new Error('Failed to submit practice');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error submitting practice. Please try again.');
        }
    });

    // Helper function to update totals
    function updateTotals() {
        const minutes = {};
        document.querySelectorAll('.practice-input').forEach(input => {
            minutes[input.dataset.day] = input.value || '0';
        });
        
        const { grade, totalMinutes, practiceDays, maxPossiblePoints } = calculateGrade(minutes);
        
        document.getElementById('totalMinutes').textContent = totalMinutes;
        document.getElementById('daysPracticed').textContent = practiceDays;
        document.getElementById('estimatedGrade').textContent = 
            `${grade}/85 (${maxPossiblePoints}/105 with parent signature)`;
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

    // Initialize sorting state
    let currentSort = {
        column: null,
        direction: 'asc'
    };

    // Handle sorting for tables with sortable headers
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.sort;
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Update sort direction
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = column;
                currentSort.direction = 'asc';
            }
            
            // Update sort icons
            document.querySelectorAll('.sortable i').forEach(icon => {
                icon.className = 'fas fa-sort';
            });
            this.querySelector('i').className = `fas fa-sort-${currentSort.direction === 'asc' ? 'up' : 'down'}`;
            
            // Sort rows
            rows.sort((a, b) => {
                let aValue, bValue;
                
                // Get values based on column
                if (column === 'lastName') {
                    aValue = a.cells[0].textContent.trim();
                    bValue = b.cells[0].textContent.trim();
                } else if (column === 'firstName') {
                    aValue = a.cells[1].textContent.trim();
                    bValue = b.cells[1].textContent.trim();
                } else if (column === 'instrument') {
                    // Define instrument order
                    const instrumentOrder = {
                        'Flute': 1, 'Oboe': 2, 'Clarinet': 3, 'Bassoon': 4, 'Saxophone': 5,
                        'Trumpet': 6, 'Horn': 7, 'Trombone': 8, 'Euphonium': 9, 'Tuba': 10,
                        'Percussion': 11
                    };
                    
                    // Get instrument names and their order values
                    aValue = instrumentOrder[a.cells[2].textContent.trim()] || 999;
                    bValue = instrumentOrder[b.cells[2].textContent.trim()] || 999;
                } else if (column === 'minutes') {
                    aValue = parseInt(a.cells[3].textContent) || 0;
                    bValue = parseInt(b.cells[3].textContent) || 0;
                } else if (column === 'days') {
                    // Extract just the number from the days cell (before any badges)
                    aValue = parseInt(a.cells[4].textContent.trim().split(' ')[0]) || 0;
                    bValue = parseInt(b.cells[4].textContent.trim().split(' ')[0]) || 0;
                } else if (column === 'signature') {
                    // Sort by signature status (approved > pending > denied > no)
                    const getSignatureValue = (cell) => {
                        const badge = cell.querySelector('.badge');
                        if (!badge) return 0;
                        if (badge.textContent.includes('Yes')) return 3;
                        if (badge.textContent.includes('Pending')) return 2;
                        if (badge.textContent.includes('Denied')) return 1;
                        return 0;
                    };
                    aValue = getSignatureValue(a.cells[5]);
                    bValue = getSignatureValue(b.cells[5]);
                } else if (column === 'grade') {
                    // Extract just the number from "X/105" format
                    aValue = parseInt(a.cells[6].textContent.split('/')[0]) || 0;
                    bValue = parseInt(b.cells[6].textContent.split('/')[0]) || 0;
                }
                
                // Handle numeric sorting
                if (typeof aValue === 'number' && typeof bValue === 'number') {
                    return (aValue - bValue) * (currentSort.direction === 'asc' ? 1 : -1);
                }
                
                // Handle string sorting
                return String(aValue).localeCompare(String(bValue)) * (currentSort.direction === 'asc' ? 1 : -1);
            });
            
            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        });
    });

    // Handle practice details view
    document.querySelectorAll('.view-details').forEach(button => {
        button.addEventListener('click', function() {
            const minutes = JSON.parse(this.dataset.minutes || '{}');
            const comments = JSON.parse(this.dataset.comments || '{}');
            const student = this.dataset.student;
            const days = ['friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday'];
            
            document.querySelector('.modal-title').textContent = `${student}'s Practice Details`;
            
            const tbody = document.getElementById('detailsBody');
            tbody.innerHTML = '';
            
            days.forEach(day => {
                const row = document.createElement('tr');
                const dayMinutes = minutes[day] || 0;
                row.innerHTML = `
                    <td>${day.charAt(0).toUpperCase() + day.slice(1)}</td>
                    <td>${dayMinutes} minutes</td>
                    <td>${comments[day] || '-'}</td>
                `;
                if (dayMinutes > 0) {
                    row.classList.add('table-success');
                }
                tbody.appendChild(row);
            });
        });
    });
});
