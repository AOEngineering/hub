const signals = [
  {
    title: "Vacancy + code violations",
    description:
      "Flag homes with utility shutoffs, board-ups, or city maintenance notices."
  },
  {
    title: "Probate + absentee owners",
    description:
      "Identify heirs or out-of-state owners who may want a fast cash exit."
  },
  {
    title: "Tax delinquency",
    description:
      "Surface owners behind on taxes and offer a quick close before penalties mount."
  }
];

const workflow = [
  {
    step: "1. Ingest",
    detail: "Pull county records, MLS feeds, and public code enforcement data."
  },
  {
    step: "2. Enrich",
    detail: "Append skip-trace contact info, email lookups, and LLC ownership trails."
  },
  {
    step: "3. Outreach",
    detail: "Queue personalized emails, direct mail, and call scripts."
  },
  {
    step: "4. Track",
    detail: "Log responses, schedule walk-throughs, and attach rehab notes."
  }
];

export default function HomePage() {
  return (
    <main className="main">
      <section className="hero">
        <div>
          <p className="hero__eyebrow">Cash buyer pipeline</p>
          <h1>Source distressed Cleveland properties before they hit the market.</h1>
          <p className="hero__lead">
            Build a targeted list of rough homes, match owners with quick cash
            offers, and track finder payouts in one place.
          </p>
          <div className="hero__actions">
            <button className="primary">Create a lead list</button>
            <button className="secondary">See sample outreach</button>
          </div>
        </div>
        <div className="hero__panel">
          <h2>Lead snapshot</h2>
          <div className="lead-card">
            <div>
              <p className="lead-card__label">Target address</p>
              <p className="lead-card__value">2418 East 55th St, Cleveland</p>
            </div>
            <div className="lead-card__grid">
              <div>
                <p className="lead-card__label">Condition</p>
                <p className="lead-card__value">Vacant · boarded</p>
              </div>
              <div>
                <p className="lead-card__label">Owner status</p>
                <p className="lead-card__value">Out-of-state LLC</p>
              </div>
              <div>
                <p className="lead-card__label">Next action</p>
                <p className="lead-card__value">Send cash offer email</p>
              </div>
            </div>
            <div className="lead-card__footer">
              <span>Finder fee ready</span>
              <span className="pill">$1,500</span>
            </div>
          </div>
        </div>
      </section>

      <section id="workflow" className="section">
        <div className="section__title">
          <h2>Turn public data into an acquisition machine</h2>
          <p>
            Automate the end-to-end workflow so the investor can focus on
            walkthroughs and rehab projections.
          </p>
        </div>
        <div className="card-grid">
          {workflow.map((item) => (
            <div className="card" key={item.step}>
              <h3>{item.step}</h3>
              <p>{item.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="signals" className="section section--accent">
        <div className="section__title">
          <h2>Signals that indicate a fast-cash opportunity</h2>
          <p>
            Mix county data with local intel to find the owners most likely to
            sell quickly.
          </p>
        </div>
        <div className="card-grid">
          {signals.map((signal) => (
            <div className="card card--outline" key={signal.title}>
              <h3>{signal.title}</h3>
              <p>{signal.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="contact" className="section section--split">
        <div>
          <h2>Finder network dashboard</h2>
          <p>
            Track who brought each deal, log rehab scope, and issue finder fees
            automatically once the property closes.
          </p>
          <ul className="feature-list">
            <li>Deal stages with inspection notes.</li>
            <li>Owner contact history and last touchpoint.</li>
            <li>Exportable cash buyer scripts and mailers.</li>
          </ul>
        </div>
        <div className="panel">
          <h3>Next step</h3>
          <p>
            Drop your first target neighborhood and we will generate a custom
            lead list.
          </p>
          <form className="form">
            <label>
              Neighborhood focus
              <input type="text" placeholder="e.g. Slavic Village" />
            </label>
            <label>
              Contact email
              <input type="email" placeholder="you@email.com" />
            </label>
            <button type="submit" className="primary">
              Build my list
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
