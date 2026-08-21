const TermsOfService = () => {
  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-16">
        <h1 className="text-4xl font-extrabold tracking-tight mb-8">Terms of Service</h1>
        <p className="text-slate-500 mb-8">Last updated: May 18, 2026</p>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4">1. Acceptance of Terms</h2>
            <p className="text-slate-300 leading-relaxed">
              By accessing or using the Autergo AI Interview System ("Service"), you agree to be bound
              by these Terms of Service ("Terms"). If you do not agree to these Terms, do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">2. Description of Service</h2>
            <p className="text-slate-300 leading-relaxed">
              Autergo provides an AI-powered interview platform that enables:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>AI-conducted technical and behavioral interviews</li>
              <li>Automated scoring and feedback generation</li>
              <li>Interview management for HR professionals</li>
              <li>Analytics and reporting on candidate performance</li>
              <li>Certificate generation for completed interviews</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">3. User Accounts</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              You are responsible for maintaining the confidentiality of your account credentials.
              You agree to:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Provide accurate and complete registration information</li>
              <li>Maintain the security of your password</li>
              <li>Accept responsibility for all activities under your account</li>
              <li>Notify us immediately of any unauthorized access</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">4. Acceptable Use</h2>
            <p className="text-slate-300 leading-relaxed mb-4">You agree not to:</p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Use the Service for any unlawful purpose</li>
              <li>Attempt to manipulate or cheat the AI evaluation system</li>
              <li>Share your account credentials with others</li>
              <li>Use automated tools to access the Service without authorization</li>
              <li>Interfere with or disrupt the Service or servers</li>
              <li>Collect or harvest user data without consent</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">5. Intellectual Property</h2>
            <p className="text-slate-300 leading-relaxed">
              The Service and its original content, features, and functionality are owned by Autergo
              and are protected by international copyright, trademark, and other intellectual property laws.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">6. Limitation of Liability</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              To the maximum extent permitted by law, Autergo shall not be liable for:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Indirect, incidental, special, or consequential damages</li>
              <li>Loss of profits, data, or business opportunities</li>
              <li>Accuracy of AI-generated evaluations and scores</li>
              <li>Service interruptions or data loss</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">7. Disclaimer of Warranties</h2>
            <p className="text-slate-300 leading-relaxed">
              The Service is provided "as is" and "as available" without warranties of any kind,
              either express or implied, including but not limited to merchantability, fitness for
              a particular purpose, and non-infringement.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">8. Termination</h2>
            <p className="text-slate-300 leading-relaxed">
              We may terminate or suspend your account and access to the Service immediately,
              without prior notice, for conduct that we believe violates these Terms or is harmful
              to other users, us, or third parties, or for any other reason.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">9. Governing Law</h2>
            <p className="text-slate-300 leading-relaxed">
              These Terms shall be governed by and construed in accordance with the laws of the
              jurisdiction in which Autergo operates, without regard to conflict of law principles.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">10. Changes to Terms</h2>
            <p className="text-slate-300 leading-relaxed">
              We reserve the right to modify these Terms at any time. We will notify users of
              material changes via email or through the Service. Continued use of the Service
              after changes constitutes acceptance of the new Terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">11. Contact</h2>
            <p className="text-slate-300 leading-relaxed">
              For questions about these Terms, please contact us at legal@autergo.ai
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default TermsOfService;
