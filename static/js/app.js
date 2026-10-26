/**
 * Multimodal Attendance & Engagement Agent - Frontend Interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    initFlashDismiss();
    initAttendanceRadioToggles();
    initEngagementSimulator();
    initStudentModals();
});

/* -------------------------------------------------------------
   Flash Alert Dismissal
   ------------------------------------------------------------- */
function initFlashDismiss() {
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const alert = e.target.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 200);
            }
        });
    });
}

/* -------------------------------------------------------------
   Attendance Radio Toggles & Bulk Actions
   ------------------------------------------------------------- */
function initAttendanceRadioToggles() {
    const radioLabels = document.querySelectorAll('.status-radio-label');
    
    radioLabels.forEach(label => {
        const input = label.querySelector('input[type="radio"]');
        if (!input) return;

        // Initial styling
        if (input.checked) {
            updateRadioStyle(label, input.value);
        }

        input.addEventListener('change', () => {
            // Unstyle siblings in this group
            const group = label.closest('.status-radio-group');
            if (group) {
                group.querySelectorAll('.status-radio-label').forEach(sibling => {
                    sibling.classList.remove('is-present', 'is-absent');
                });
            }
            updateRadioStyle(label, input.value);
            updateAttendanceSummaryBar();
        });
    });

    // Bulk buttons: Mark All Present / Mark All Absent
    const markAllPresentBtn = document.getElementById('btnMarkAllPresent');
    const markAllAbsentBtn = document.getElementById('btnMarkAllAbsent');

    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', () => {
            document.querySelectorAll('input[type="radio"][value="Present"]').forEach(radio => {
                radio.checked = true;
                const label = radio.closest('.status-radio-label');
                const group = label.closest('.status-radio-group');
                group.querySelectorAll('.status-radio-label').forEach(s => s.classList.remove('is-present', 'is-absent'));
                updateRadioStyle(label, 'Present');
            });
            updateAttendanceSummaryBar();
        });
    }

    if (markAllAbsentBtn) {
        markAllAbsentBtn.addEventListener('click', () => {
            document.querySelectorAll('input[type="radio"][value="Absent"]').forEach(radio => {
                radio.checked = true;
                const label = radio.closest('.status-radio-label');
                const group = label.closest('.status-radio-group');
                group.querySelectorAll('.status-radio-label').forEach(s => s.classList.remove('is-present', 'is-absent'));
                updateRadioStyle(label, 'Absent');
            });
            updateAttendanceSummaryBar();
        });
    }
}

function updateRadioStyle(label, val) {
    if (val === 'Present') {
        label.classList.add('is-present');
        label.classList.remove('is-absent');
    } else if (val === 'Absent') {
        label.classList.add('is-absent');
        label.classList.remove('is-present');
    }
}

function updateAttendanceSummaryBar() {
    const allGroups = document.querySelectorAll('.status-radio-group');
    if (!allGroups.length) return;

    let present = 0;
    let absent = 0;

    allGroups.forEach(group => {
        const checked = group.querySelector('input[type="radio"]:checked');
        if (checked) {
            if (checked.value === 'Present') present++;
            if (checked.value === 'Absent') absent++;
        }
    });

    const total = allGroups.length;
    const pct = total > 0 ? ((present / total) * 100).toFixed(1) : 0;

    const summaryPresent = document.getElementById('summaryPresentCount');
    const summaryAbsent = document.getElementById('summaryAbsentCount');
    const summaryPct = document.getElementById('summaryPercentage');

    if (summaryPresent) summaryPresent.textContent = present;
    if (summaryAbsent) summaryAbsent.textContent = absent;
    if (summaryPct) summaryPct.textContent = `${pct}%`;
}

/* -------------------------------------------------------------
   Interactive Engagement Simulator
   ------------------------------------------------------------- */
function initEngagementSimulator() {
    const activitySelect = document.getElementById('simActivityLevel');
    const inactivityInput = document.getElementById('simInactivityMinutes');
    const inactivityDisplay = document.getElementById('inactivityValDisplay');
    const audioSelect = document.getElementById('simAudioActivity');

    if (!activitySelect || !inactivityInput || !audioSelect) return;

    function recalculateScore() {
        const activity = activitySelect.value;
        const inactivity = parseInt(inactivityInput.value) || 0;
        const audio = audioSelect.value;

        if (inactivityDisplay) {
            inactivityDisplay.textContent = `${inactivity} min`;
        }

        fetch('/api/calculate-engagement', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                activity_level: activity,
                inactivity_minutes: inactivity,
                audio_activity: audio
            })
        })
        .then(res => res.json())
        .then(data => {
            updateEngagementPreviewUI(data);
        })
        .catch(err => {
            // Client-side fallback calculation if API fails
            const actPts = activity === 'High' ? 40 : (activity === 'Medium' ? 28 : 12);
            let inactPts = 2;
            if (inactivity <= 5) inactPts = 35;
            else if (inactivity <= 15) inactPts = 25;
            else if (inactivity <= 30) inactPts = 12;

            const audPts = audio === 'High' ? 25 : (audio === 'Medium' ? 18 : 8);
            const total = Math.min(100, actPts + inactPts + audPts);

            let cat = 'Low Engagement';
            let badge = 'badge-danger';
            if (total >= 75) { cat = 'High Engagement'; badge = 'badge-high'; }
            else if (total >= 50) { cat = 'Moderate Engagement'; badge = 'badge-warning'; }

            updateEngagementPreviewUI({
                score: total,
                category: cat,
                badge_color: badge,
                description: 'Estimated based on multimodal classroom cues.',
                breakdown: {
                    activity_pts: actPts,
                    inactivity_pts: inactPts,
                    audio_pts: audPts
                },
                suggestions: [
                    inactivity >= 20 ? "Prolonged Inactivity: Engage with questions or break." : "Continue balanced teaching."
                ]
            });
        });
    }

    activitySelect.addEventListener('change', recalculateScore);
    inactivityInput.addEventListener('input', recalculateScore);
    audioSelect.addEventListener('change', recalculateScore);
}

function updateEngagementPreviewUI(data) {
    const scoreVal = document.getElementById('liveScoreValue');
    const catBadge = document.getElementById('liveCategoryBadge');
    const catDesc = document.getElementById('liveCategoryDesc');
    const actPts = document.getElementById('ptsActivity');
    const inactPts = document.getElementById('ptsInactivity');
    const audPts = document.getElementById('ptsAudio');
    const sugContainer = document.getElementById('liveSuggestionsList');

    if (scoreVal) scoreVal.textContent = data.score;
    if (catBadge) {
        catBadge.textContent = data.category;
        catBadge.className = `badge ${data.badge_color === 'success' || data.badge_color === 'badge-high' ? 'badge-high' : (data.badge_color === 'warning' ? 'badge-warning' : 'badge-low')}`;
    }
    if (catDesc && data.description) catDesc.textContent = data.description;

    if (actPts && data.breakdown) actPts.textContent = `${data.breakdown.activity_pts} / 40`;
    if (inactPts && data.breakdown) inactPts.textContent = `${data.breakdown.inactivity_pts} / 35`;
    if (audPts && data.breakdown) audPts.textContent = `${data.breakdown.audio_pts} / 25`;

    if (sugContainer && data.suggestions) {
        sugContainer.innerHTML = '';
        data.suggestions.forEach(sug => {
            const li = document.createElement('li');
            li.className = 'suggestion-item';
            li.innerHTML = `
                <span class="suggestion-icon">💡</span>
                <div class="suggestion-content">
                    <strong>Teaching Recommendation</strong>
                    <p>${sug}</p>
                </div>
            `;
            sugContainer.appendChild(li);
        });
    }
}

/* -------------------------------------------------------------
   Student Management Modals (Edit & Delete Confirmation)
   ------------------------------------------------------------- */
function initStudentModals() {
    const editModal = document.getElementById('editStudentModal');
    const deleteModal = document.getElementById('deleteStudentModal');

    // Close buttons
    document.querySelectorAll('.modal-close-trigger').forEach(btn => {
        btn.addEventListener('click', () => {
            if (editModal) editModal.classList.remove('active');
            if (deleteModal) deleteModal.classList.remove('active');
        });
    });

    // Close on clicking backdrop
    window.addEventListener('click', (e) => {
        if (e.target === editModal) editModal.classList.remove('active');
        if (e.target === deleteModal) deleteModal.classList.remove('active');
    });

    // Edit button click handlers
    document.querySelectorAll('.btn-edit-student').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-id');
            const name = btn.getAttribute('data-name');
            const roll = btn.getAttribute('data-roll');
            const cls = btn.getAttribute('data-class');

            const form = document.getElementById('editStudentForm');
            if (form) {
                form.action = `/students/edit/${id}`;
                document.getElementById('editStudentName').value = name;
                document.getElementById('editStudentRoll').value = roll;
                document.getElementById('editStudentClass').value = cls;
            }
            if (editModal) editModal.classList.add('active');
        });
    });

    // Delete button click handlers
    document.querySelectorAll('.btn-delete-student').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-id');
            const name = btn.getAttribute('data-name');
            const roll = btn.getAttribute('data-roll');

            const form = document.getElementById('deleteStudentForm');
            const nameTarget = document.getElementById('deleteStudentNameTarget');
            if (form) {
                form.action = `/students/delete/${id}`;
            }
            if (nameTarget) {
                nameTarget.textContent = `${name} (${roll})`;
            }
            if (deleteModal) deleteModal.classList.add('active');
        });
    });
}
