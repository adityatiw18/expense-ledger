function CreateLedger({
  previousLedgers,
  handleOpenLedger,

  setupName,
  setupEmail,
  setupGroupName,
  setupMembers,
  actionLoading,
  errorMessage,

  setSetupName,
  setSetupEmail,
  setSetupGroupName,

  handleSetupMemberChange,
  addSetupMember,
  removeSetupMember,
  handleCreateLedger,
}) {
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">
            EXPENSE LEDGER / 01
          </p>

          <h1>Create Ledger</h1>

          <p className="group-status">
            SET UP YOUR FIRST LEDGER
          </p>
        </div>

        <div className="group-meta">
          <span>NEW LEDGER</span>
        </div>
      </header>

      {errorMessage && (
        <div
          style={{
            margin: "0 auto 24px",
            maxWidth: "1140px",
            padding: "12px 16px",
            border: "1px solid #b83a2d",
            borderRadius: "6px",
            background: "#f1e6d0",
            color: "#8f2d23",
            fontFamily: "DM Mono, monospace",
          }}
        >
          {errorMessage}
        </div>
      )}

      <main className="content">

        {/* PREVIOUS LEDGERS */}

        {/* PREVIOUS LEDGERS */}

<section
  className="transactions-section"
  style={{ marginBottom: "48px" }}
>
  <div className="section-heading">
    <span>01</span>
    <h2>Previous Ledgers</h2>
  </div>

  {previousLedgers.length === 0 ? (
    <div className="modal-placeholder">
      No previous ledgers found.
    </div>
  ) : (
    <div className="transaction-card">
      {previousLedgers.map((ledger) => (
        <div
          className="transaction-row"
          key={ledger.id}
        >
          <div>
            <span className="transaction-title">
              {ledger.name}
            </span>

            <span className="transaction-meta">
              Created{" "}
              {new Date(ledger.created_at).toLocaleDateString(
                "en-IN",
                {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                }
              )}
            </span>
          </div>

          <button
            className="action-button secondary"
            onClick={() => handleOpenLedger(ledger)}
            type="button"
          >
            Open →
          </button>
        </div>
      ))}
    </div>
  )}
</section>

        {/* YOUR DETAILS */}

        <section className="balance-section">
          <div className="section-heading">
            <span>02</span>
            <h2>Your Details</h2>
          </div>

          <div className="expense-form">

            <label>
              Your Name

              <input
                type="text"
                placeholder="e.g. Aditya"
                value={setupName}
                onChange={(e) =>
                  setSetupName(e.target.value)
                }
              />
            </label>

            <label>
              Your Email

              <input
                type="email"
                placeholder="e.g. aditya@example.com"
                value={setupEmail}
                onChange={(e) =>
                  setSetupEmail(e.target.value)
                }
              />
            </label>

            <label>
              Ledger Name

              <input
                type="text"
                placeholder="e.g. Goa Trip"
                value={setupGroupName}
                onChange={(e) =>
                  setSetupGroupName(e.target.value)
                }
              />
            </label>

          </div>
        </section>

        {/* MEMBERS */}

        <section className="transactions-section">
          <div className="section-heading">
            <span>03</span>
            <h2>Members</h2>
          </div>

          <div className="transaction-card setup-members-card">
            {setupMembers.map((member, index) => (
              <div
                className="setup-member-row"
                key={index}
              >
                <div className="setup-member-fields">

                  <input
                    type="text"
                    placeholder="Member name"
                    value={member.name}
                    onChange={(e) =>
                      handleSetupMemberChange(
                        index,
                        "name",
                        e.target.value
                      )
                    }
                  />

                  <input
                    type="email"
                    placeholder="Member email"
                    value={member.email}
                    onChange={(e) =>
                      handleSetupMemberChange(
                        index,
                        "email",
                        e.target.value
                      )
                    }
                  />

                </div>

                {setupMembers.length > 1 && (
                  <button
                    className="modal-close setup-member-remove"
                    onClick={() =>
                      removeSetupMember(index)
                    }
                    type="button"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              gap: "12px",
              marginTop: "20px",
              flexWrap: "wrap",
            }}
          >
            <button
              className="action-button secondary"
              onClick={addSetupMember}
              type="button"
            >
              + Add Member
            </button>

            <button
              className="action-button primary"
              onClick={handleCreateLedger}
              disabled={actionLoading === "setup"}
              type="button"
            >
              {actionLoading === "setup"
                ? "Creating..."
                : "Create Ledger"}
            </button>
          </div>
        </section>

      </main>
    </div>
  );
}

export default CreateLedger;