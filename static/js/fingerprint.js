/**
 * MicroEarnX Advanced Canvas & Hardware Fingerprinting
 * Ensures 1 Device = 1 Account Strict Restriction
 */
(function generateDeviceFingerprint() {
    try {
        // ১. ক্যানভাস ফিঙ্গারপ্রিন্ট রেন্ডারিং
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 200;
        canvas.height = 50;

        ctx.textBaseline = "top";
        ctx.font = "16px 'Arial'";
        ctx.fillStyle = "#4f46e5";
        ctx.fillRect(10, 10, 100, 30);
        ctx.fillStyle = "#10b981";
        ctx.fillText("MicroEarnX#DeviceSecurity", 12, 15);

        const canvasData = canvas.toDataURL();

        // ২. হার্ডওয়্যার ও স্ক্রিন মেট্রিক্স সংগ্রহ
        const screenSpecs = `${screen.width}x${screen.height}x${screen.colorDepth}`;
        const cores = navigator.hardwareConcurrency || "NA";
        const lang = navigator.language || "NA";
        const userAgent = navigator.userAgent;

        // ৩. স্ট্রিং কম্বিনেশন তৈরি
        const rawString = `${canvasData}__${screenSpecs}__${cores}__${lang}__${userAgent}`;

        // ৪. হ্যাশ জেনারেশন (Simple Fast Hash)
        let hash = 0;
        for (let i = 0; i < rawString.length; i++) {
            const char = rawString.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash |= 0; // Convert to 32bit integer
        }

        const deviceUUID = "DEV-" + Math.abs(hash).toString(16).toUpperCase();

        // ৫. LocalStorage এ স্থায়ীভাবে সংরক্ষণ
        let persistentId = localStorage.getItem('mx_device_identity');
        if (!persistentId) {
            persistentId = deviceUUID;
            localStorage.setItem('mx_device_identity', persistentId);
        }

        // ৬. ফর্মে ডিভাইস আইডি অটো-ইনজেক্ট করা
        document.addEventListener("DOMContentLoaded", function () {
            const deviceInputs = document.querySelectorAll('input[name="device_id"]');
            deviceInputs.forEach(input => {
                input.value = persistentId;
            });
        });

    } catch (e) {
        console.error("Device fingerprinting failed:", e);
    }
})();
