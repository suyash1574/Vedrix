const AccessibilityStatement = () => {
  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-16">
        <h1 className="text-4xl font-extrabold tracking-tight mb-8">Accessibility Statement</h1>
        <p className="text-slate-500 mb-8">Last updated: May 18, 2026</p>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4">Our Commitment</h2>
            <p className="text-slate-300 leading-relaxed">
              Autergo is committed to ensuring digital accessibility for people with disabilities.
              We are continually improving the user experience for everyone and applying the
              relevant accessibility standards to ensure we provide equal access to all of our users.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">Conformance Status</h2>
            <p className="text-slate-300 leading-relaxed">
              The Web Content Accessibility Guidelines (WCAG) defines requirements for designers
              and developers to improve accessibility for people with disabilities. It defines
              three levels of conformance: Level A, Level AA, and Level AAA.
            </p>
            <p className="text-slate-300 leading-relaxed mt-4">
              Autergo is partially conformant with <strong className="text-purple-400">WCAG 2.1 Level AA</strong>.
              Partially conformant means that some parts of the content do not fully conform
              to the accessibility standard.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">Accessibility Features</h2>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Keyboard navigation support for all interactive elements</li>
              <li>ARIA labels on all interactive components</li>
              <li>Focus indicators visible on all interactive elements</li>
              <li>Color contrast ratios meeting AA standards (4.5:1 for text)</li>
              <li>Screen reader compatibility with NVDA and VoiceOver</li>
              <li>Logical heading structure throughout the application</li>
              <li>Descriptive link text and button labels</li>
              <li>Error messages announced to screen readers</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">Technologies Used</h2>
            <p className="text-slate-300 leading-relaxed">
              Accessibility of Autergo relies on the following technologies to work with the
              particular combination of web browser and any assistive technologies or plugins
              installed on your computer:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>HTML5</li>
              <li>WAI-ARIA</li>
              <li>CSS</li>
              <li>JavaScript</li>
              <li>React</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">Known Limitations</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              Despite our best efforts to ensure accessibility of Autergo, there may be some limitations.
              Below is a description of known limitations:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Some third-party AI-generated content may not be fully accessible</li>
              <li>Certificate PDF generation may have limited screen reader support</li>
              <li>Real-time interview interface may have limited keyboard navigation</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">Feedback</h2>
            <p className="text-slate-300 leading-relaxed">
              We welcome your feedback on the accessibility of Autergo. Please let us know if you
              encounter accessibility barriers:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Email: accessibility@autergo.ai</li>
              <li>We try to respond to feedback within 5 business days</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4">Assessment Approach</h2>
            <p className="text-slate-300 leading-relaxed">
              Autergo assessed the accessibility of this website by the following approaches:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
              <li>Self-evaluation using automated testing tools</li>
              <li>Testing with screen readers (NVDA, VoiceOver)</li>
              <li>Keyboard-only navigation testing</li>
              <li>Color contrast analysis</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
};

export default AccessibilityStatement;
