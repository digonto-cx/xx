# ⚡ MicroEarnX — Serverless Micro-Task & Earning Platform

<p align="center">
  <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1200&auto=format&fit=crop" alt="MicroEarnX Banner" width="100%" style="border-radius: 10px;"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.0.3-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" />
  <img src="https://img.shields.io/badge/Deployed%20on-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" />
  <img src="https://img.shields.io/badge/Storage-ImgBB%20Failover-0084FF?style=for-the-badge" />
</p>

---

## 📌 প্রোজেক্ট পরিচিতি (Overview)
**MicroEarnX** হলো একটি আধুনিক, স্কেলেবল এবং লাইটওয়েট মাইক্রো-আর্নিং প্ল্যাটফর্ম। এটি সম্পূর্ণ **Serverless আর্কিটেকচারে (Flask + Vercel)** তৈরি এবং ডেটাবেস হিসেবে ব্যবহার করা হয়েছে **Supabase (PostgreSQL)**।

সাইটটিতে রয়েছে কঠোর ফ্রড প্রিভেনশন (Device Fingerprinting), ডাইনামিক রেফারেল বোনাস, টাস্ক ম্যানেজমেন্ট এবং অ্যাডমিনদের কাজের সুবিধার জন্য **স্মার্ট বাল্ক অ্যাপ্রুভাল সিস্টেম**।

---

## 🖼️ ইন্টারফেস প্রিভিউ (UI Screenshots)

| 📱 ইউজার ড্যাশবোর্ড (`/app`) | 📋 টাস্ক এবং প্রুফ সাবমিট (`/tasks`) |
| :---: | :---: |
| <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=600&auto=format&fit=crop" width="100%" alt="User Dashboard"/> | <img src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=600&auto=format&fit=crop" width="100%" alt="Task Submission"/> |

| 🛡️ অ্যাডমিন ড্যাশবোর্ড (`/admin`) | ⚡ বাল্ক রিভিউ ইঞ্জিন (`/admin/submit`) |
| :---: | :---: |
| <img src="https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?q=80&w=600&auto=format&fit=crop" width="100%" alt="Admin Panel"/> | <img src="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=600&auto=format&fit=crop" width="100%" alt="Bulk Review Engine"/> |

---

## 🚀 প্রধান ফিচারসমূহ (Key Features)

### 💰 আর্নিং এবং রেফারেল লজিক
- **স্মার্ট সাইন-আপ বোনাস:**
  - সাধারণ সাইন-আপ: **৫০ টাকা**
  - রেফারেল লিংকের মাধ্যমে সাইন-আপ: **১০০ টাকা**
  - প্রতি সফল রেফারেলে রেফারার পাবে: **১৫ টাকা**
- **অ্যান্টি-ফ্রড ডিভাইস প্রোটেকশন (Anti-Cheat):**
  - ব্রাউজার ক্যানভাস এবং স্ক্রিন ফিঙ্গারপ্রিন্ট ট্র্যাকিং।
  - **১টি ডিভাইসে কেবল ১টি অ্যাকাউন্ট** খোলার কঠোর সীমাবদ্ধতা।
  - নিজের ডিভাইসে নিজে রেফার করা সম্পূর্ণ ব্লক।

### 📸 ImgBB Multi-Key Failover Engine
- একাধিক ImgBB API Key যুক্ত করার সুবিধা।
- যদি কোনো একটি কি-এর লিমিট শেষ হয়ে যায় বা ফেইল করে, সিস্টেম স্বয়ংক্রিয়ভাবে পরবর্তী কি (Next API Key) ব্যবহার করে ইমেজ আপলোড সম্পন্ন করবে।

### 🛡️ সুপার অ্যাডমিন কন্ট্রোল প্যানেল
- **অ্যাডমিন অ্যানালিটিক্স:** মোট ইউজার, আজকের জয়েনিং, গতকালের ইউজার এবং পেন্ডিং টাস্ক রিয়েলটাইমে দেখা যায়।
- **সাইট নোটিশ ইঞ্জিন:** অ্যাডমিন প্যানেল থেকে নোটিশ পরিবর্তন করলে তা সব ইউজারের ড্যাশবোর্ডে ভেসে উঠবে।
- **ইউজার ম্যানেজমেন্ট:** ব্যালেন্স যোগ/বিয়োগ, সার্চ, ব্যান/আনব্যান ও ডিলিট অপশন।
- **উইথড্রয়াল মনিটরিং:** উইথড্র রিকোয়েস্টের সাথে ইউজারের পূর্বের মোট রিজেকশন সংখ্যা দৃশ্যমান।
- **বাল্ক সাবমিশন ইঞ্জিন:** এক ক্লিকে সর্বোচ্চ ৩০টি টাস্কের মধ্যে **যেকোনো ৩টি র‍্যান্ডম রিজেক্ট** করে বাকি ২৭টি অটোমেটিক অ্যাপ্রুভ ও পেমেন্ট ক্রেডিট।

### 💸 উইথড্রয়াল রুলস
- মিনিমাম উইথড্রয়াল ব্যালেন্স: **৫০০ টাকা**
- বাধ্যতামূলক শর্ত: সর্বনিম্ন **৪টি সফল রেফারেল** থাকতে হবে।

---

## 🛠️ সিস্টেম আর্কিটেকচার (System Workflow)

```mermaid
graph TD
    User([ইউজার ডিভাইস]) -->|Browser Fingerprint| Auth{রেজিস্ট্রেশন চেক}
    Auth -->|একই ডিভাইস?| Block[⛔ অ্যাকাউন্ট ব্লক]
    Auth -->|নতুন ডিভাইস| DB[(Supabase PostgreSQL)]
    
    User -->|টাস্ক স্ক্রিনশট আপলোড| ImgBBEngine{ImgBB Failover}
    ImgBBEngine -->|Key 1 Failed| Key2[Try Key 2]
    ImgBBEngine -->|Success| SaveTask[সাবমিশন সেভ]
    
    SaveTask --> AdminSubmit[/admin/submit]
    AdminSubmit -->|Bulk Action Run| BulkEngine{ম্যাক্সিমাম ৩০টি টাস্ক}
    BulkEngine -->|অটোমেটিক ৩টি| Reject[❌ রিজেক্ট]
    BulkEngine -->|বাকি ২৭টি| Approve[✅ অ্যাপ্রুভ + টাকা ক্রেডিট]
