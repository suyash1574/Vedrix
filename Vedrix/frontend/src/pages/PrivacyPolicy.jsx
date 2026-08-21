const PrivacyPolicy = () => {
  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-16">
        <h1 className="text-4xl font-extrabold tracking-tight mb-8">Privacy Policy</h1>
        <p className="text-slate-500 mb-8">Last updated: May 18, 2026</p>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4">1. Introduction</h2>
            <p className="text-slate-300 leading-relaxed">
              Autergo AI Interview System ("we", "our", or "us") is committed to protecting your privacy.
              This Privacy Policy explains how we collect, use, disclose, and safeguard your information
              when you use our AI-powered interview platform.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">2. Information We Collect</h2>
            <h3 className="text-xl font-bold mb-2 text-purple-400">2.1 Personal Information</h3>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Name, email address, and username</li>
              <li>Profile information (company, department, position)</li>
              <li>Account credentials and authentication data</li>
            </ul>

            <h3 className="text-xl font-bold mb-2 text-purple-400 mt-6">2.2 Interview Data</h3>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Interview responses and transcripts</li>
              <li>AI-generated scores and feedback</li>
              <li>Skill assessments and evaluations</li>
              <li>Interview duration and timing data</li>
            </ul>

            <h3 className="text-xl font-bold mb-2 text-purple-400 mt-6">2.3 Technical Information</h3>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>IP address and device information</li>
              <li>Browser type and operating system</li>
              <li>Usage patterns and interaction data</li>
              <li>Cookies and similar technologies</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">3. How We Use Your Information</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Conduct AI-powered interview evaluations</li>
              <li>Generate interview reports and certificates</li>
              <li>Provide analytics and insights to HR users</li>
              <li>Send interview invitations and notifications</li>
              <li>Improve our AI models and platform features</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">4. Legal Basis for Processing (GDPR)</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li><strong>Contract:</strong> Processing necessary to provide interview services</li>
              <li><strong>Consent:</strong> Analytics, marketing, and AI model training</li>
              <li><strong>Legitimate Interest:</strong> Platform security, fraud prevention, service improvement</li>
              <li><strong>Legal Obligation:</strong> Compliance with applicable laws</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">5. Data Sharing and Disclosure</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We do not sell your personal information. We may share your data with:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>AI service providers (Groq, DeepSeek, NVIDIA) for interview evaluation</li>
              <li>HR users who have access to your interview results</li>
              <li>Service providers who assist in platform operations</li>
              <li>Law enforcement when required by law</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">6. Data Retention</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Interview data: Retained for 365 days</li>
              <li>Analytics data: Retained for 730 days</li>
              <li>Account data: Retained until account deletion</li>
              <li>Deleted accounts: Data permanently removed after 30-day grace period</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">7. Your Rights (GDPR)</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li><strong>Right to Access:</strong> Request a copy of your personal data</li>
              <li><strong>Right to Rectification:</strong> Correct inaccurate personal data</li>
              <li><strong>Right to Erasure:</strong> Request deletion of your personal data</li>
              <li><strong>Right to Portability:</strong> Receive your data in a standard format</li>
              <li><strong>Right to Object:</strong> Object to processing based on legitimate interest</li>
              <li><strong>Right to Withdraw Consent:</strong> Withdraw consent at any time</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">8. Data Security</h2>
            <p className="text-slate-300 leading-relaxed">
              We implement industry-standard security measures including encryption, access controls,
              and regular security audits to protect your personal information.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">9. International Data Transfers</h2>
            <p className="text-slate-300 leading-relaxed">
              Your data may be transferred to and processed in countries outside your residence.
              We ensure appropriate safeguards are in place for such transfers.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">10. Contact Us</h2>
            <p className="text-slate-300 leading-relaxed">
              For privacy-related inquiries, please contact us at privacy@autergo.ai
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
