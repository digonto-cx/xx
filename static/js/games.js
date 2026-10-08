/**
 * 1. Referral Link Copy Utility
 */
function copyReferralLink(elementId) {
    const copyText = document.getElementById(elementId);
    if (!copyText) return;
    
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(copyText.value).then(() => {
        alert("রেফারেল লিংক কপি হয়েছে!");
    }).catch(() => {
        alert("কপি করা যায়নি, ম্যানুয়ালি কপি করুন।");
    });
}

/**
 * 2. Spin Wheel Controller
 */
let isSpinning = false;
function triggerSpin() {
    if (isSpinning) return;
    isSpinning = true;

    const wheel = document.getElementById('spinWheel');
    const spinBtn = document.getElementById('spinBtn');
    if (spinBtn) spinBtn.disabled = true;

    // Flask API-তে কল করা
    fetch('/spin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            alert(data.message);
            isSpinning = false;
            if (spinBtn) spinBtn.disabled = false;
            return;
        }

        // র‍্যান্ডম রোটেশন এনিমেশন (১৮০০ থেকে ৩৬০০ ডিগ্রি)
        const randomDegree = 1800 + Math.floor(Math.random() * 360);
        wheel.style.transform = `rotate(${randomDegree}deg)`;

        setTimeout(() => {
            alert(`অভিনন্দন! আপনি ৳${data.reward} জিতেছেন!`);
            const balElement = document.getElementById('userBalance');
            if (balElement) balElement.innerText = "৳ " + data.new_balance.toFixed(2);
            isSpinning = false;
            if (spinBtn) spinBtn.disabled = false;
        }, 3200);
    })
    .catch(err => {
        alert("সার্ভার ত্রুটি! আবার চেষ্টা করুন।");
        isSpinning = false;
        if (spinBtn) spinBtn.disabled = false;
    });
}

/**
 * 3. Scratch Card Canvas Controller
 */
function initScratchCard(canvasId, rewardBoxId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let isDrawing = false;
    let scratched = false;

    // সিলভার ওভারলে আঁকা
    ctx.fillStyle = '#94a3b8';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = '16px Arial';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('ঘষে পুরস্কার দেখুন', 65, 75);

    function scratch(e) {
        if (!isDrawing || scratched) return;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - rect.left;
        const y = (e.clientY || e.touches[0].clientY) - rect.top;

        ctx.globalCompositeOperation = 'destination-out';
        ctx.beginPath();
        ctx.arc(x, y, 18, 0, Math.PI * 2);
        ctx.fill();

        // API কল করে ব্যালেন্স যুক্ত করা
        scratched = true;
        fetch('/scratch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById(rewardBoxId).innerText = `৳ ${data.reward}`;
                const balElement = document.getElementById('userBalance');
                if (balElement) balElement.innerText = "৳ " + data.new_balance.toFixed(2);
            } else {
                alert(data.message);
            }
        });
    }

    canvas.addEventListener('mousedown', () => isDrawing = true);
    canvas.addEventListener('mouseup', () => isDrawing = false);
    canvas.addEventListener('mousemove', scratch);
    canvas.addEventListener('touchmove', scratch);
    canvas.addEventListener('touchstart', () => isDrawing = true);
    canvas.addEventListener('touchend', () => isDrawing = false);
        }
