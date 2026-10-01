function Dashboard({
  groupName,
  members,
  balances,
  transactions,
  loading,
  errorMessage,
  onAddExpense,
  onSettleUp,
  onTransactionClick,
}) {
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">
            EXPENSE LEDGER / 01
          </p>

          <h1>{groupName || "Expense Ledger"}</h1>

          <p className="group-status">
            ACTIVE LEDGER · {members.length} MEMBERS
          </p>
        </div>

        <div className="group-meta">
          <span>
            {members.length}{" "}
            {members.length === 1
              ? "MEMBER"
              : "MEMBERS"}
          </span>

          <span>
            {new Date().toLocaleDateString("en-IN", {
              month: "short",
              year: "numeric",
            }).toUpperCase()}
          </span>
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
        {loading ? (
          <div className="modal-placeholder">
            Loading ledger...
          </div>
        ) : (
          <>
            {/* -------------------------------------------------
                BALANCES
            ------------------------------------------------- */}

            <section className="balance-section">
              <div className="section-heading">
                <span>01</span>
                <h2>Current Balances</h2>
              </div>

              <div className="balance-header">
                <span>MEMBER</span>
                <span>POSITION</span>
              </div>

              <div className="balance-card">
                {members.map((member) => {
                  const balance = Number(
                    balances[member.id] || 0
                  );

                  return (
                    <div
                      className="balance-row"
                      key={member.id}
                    >
                      <div>
                        <span className="member-name">
                          {member.name}
                        </span>

                        <span className="balance-label">
                          {balance > 0
                            ? "is owed"
                            : balance < 0
                              ? "owes"
                              : "is settled"}
                        </span>
                      </div>

                      <span
                        className={`amount mono ${
                          balance > 0
                            ? "positive"
                            : balance < 0
                              ? "negative"
                              : ""
                        }`}
                      >
                        {balance > 0
                          ? "+ ₹"
                          : balance < 0
                            ? "- ₹"
                            : "₹"}

                        {Math.abs(balance).toFixed(2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* -------------------------------------------------
                ACTIONS
            ------------------------------------------------- */}

            <section className="actions">
              <button
                className="action-button primary"
                onClick={onAddExpense}
              >
                + Add Expense
              </button>

              <button
                className="action-button secondary"
                onClick={onSettleUp}
              >
                Settle Up →
              </button>
            </section>

            {/* -------------------------------------------------
                RECENT TRANSACTIONS
            ------------------------------------------------- */}

            <section className="transactions-section">
              <div className="section-heading">
                <span>02</span>
                <h2>Recent Transactions</h2>
              </div>

              <div className="transaction-header">
                <span>ENTRY</span>
                <span>AMOUNT</span>
              </div>

              <div className="transaction-card">
                {transactions.length === 0 ? (
                  <div className="transaction-row">
                    <span className="transaction-title">
                      No transactions yet.
                    </span>
                  </div>
                ) : (
                  transactions.map((transaction) => (
                    <div
                      className="transaction-row"
                      key={transaction.id}
                      onClick={() =>
                        onTransactionClick(transaction.id)
                      }
                    >
                      <div>
                        <span className="transaction-title">
                          {transaction.description}
                        </span>

                        <span className="transaction-meta">
                          {transaction.paidBy} ·{" "}
                          {transaction.date}
                        </span>
                      </div>

                      <span
                        className={`transaction-amount mono ${
                          transaction.settlement
                            ? "settlement"
                            : transaction.reversal
                              ? "reversal"
                              : ""
                        }`}
                      >
                        ₹{transaction.amount.toFixed(2)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default Dashboard;