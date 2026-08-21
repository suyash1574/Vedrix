const DataProcessingAgreement = () => {
  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-16">
        <h1 className="text-4xl font-extrabold tracking-tight mb-8">Data Processing Agreement</h1>
        <p className="text-slate-500 mb-8">Last updated: May 18, 2026</p>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4">1. Parties</h2>
            <p className="text-slate-300 leading-relaxed">
              This Data Processing Agreement ("DPA") is entered into between Autergo AI Interview System
              ("Processor") and the organization using the Service ("Controller").
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">2. Purpose of Processing</h2>
            <p className="text-slate-300 leading-relaxed">
              Processor shall process personal data solely for the purpose of providing AI-powered
              interview evaluation services as described in the Service Agreement.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">3. Types of Data</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Candidate personal information (name, email)</li>
              <li>Interview responses and transcripts</li>
              <li>Evaluation scores and feedback</li>
              <li>Technical metadata (IP address, device info)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">4. Data Subject Categories</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Job candidates participating in interviews</li>
              <li>HR professionals managing interview processes</li>
              <li>System administrators</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">5. Processor Obligations</h2>
            <p className="text-slate-300 leading-relaxed mb-4">Processor shall:</p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Process data only on documented instructions from Controller</li>
              <li>Ensure personnel authorized to process data are bound by confidentiality</li>
              <li>Implement appropriate technical and organizational security measures</li>
              <li>Assist Controller in responding to data subject requests</li>
              <li>Notify Controller of any personal data breach without undue delay</li>
              <li>Delete or return all personal data upon termination of services</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">6. Sub-processors</h2>
            <p className="text-slate-300 leading-relaxed">
              Controller authorizes Processor to engage the following sub-processors:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>AI service providers (Groq, DeepSeek, NVIDIA) for interview evaluation</li>
              <li>Cloud hosting providers for infrastructure</li>
              <li>Email service providers for notifications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">7. International Transfers</h2>
            <p className="text-slate-300 leading-relaxed">
              Where personal data is transferred outside the EEA, Processor shall ensure appropriate
              safeguards are in place, including Standard Contractual Clauses or adequacy decisions.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">8. Data Retention</h2>
            <p className="text-slate-300 leading-relaxed">
              Processor shall retain personal data only for as long as necessary to fulfill the
              purposes of processing, or as required by applicable law.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">9. Audit Rights</h2>
            <p className="text-slate-300 leading-relaxed">
              Controller shall have the right to audit Processor's compliance with this DPA,
              subject to reasonable notice and during normal business hours.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">10. Contact</h2>
            <p className="text-slate-300 leading-relaxed">
              For questions about this DPA, please contact us at legal@autergo.ai
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default DataProcessingAgreement;
