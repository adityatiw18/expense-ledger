import "./App.css";
import { useEffect, useState } from "react";
import CreateLedger from "./pages/CreateLedger";

const API_URL = "http://localhost:8000";

const GROUP_STORAGE_KEY = "expenseLedgerGroupId";
const USER_STORAGE_KEY = "expenseLedgerCurrentUserId";

function App() {
  // ---------------------------------------------------------
  // Setup / persisted identity
  // ---------------------------------------------------------

  const [previousLedgers, setPreviousLedgers] = useState([]);

  const [groupId, setGroupId] = useState(() => {
    return localStorage.getItem(GROUP_STORAGE_KEY) || "";
  });

  const [currentUserId, setCurrentUserId] = useState(() => {
    return localStorage.getItem(USER_STORAGE_KEY) || "";
  });

  const [showSetup, setShowSetup] = useState(() => {
    return !localStorage.getItem(GROUP_STORAGE_KEY);
  });

  const [groupName, setGroupName] = useState("");

  // Setup form
  const [setupName, setSetupName] = useState("");
  const [setupEmail, setSetupEmail] = useState("");
  const [setupGroupName, setSetupGroupName] = useState("");
  const [setupMembers, setSetupMembers] = useState([
    { name: "", email: "" },
  ]);

  // ---------------------------------------------------------
  // Dashboard state
  // ---------------------------------------------------------

  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [description, setDescription] = useState("");
  const [balances, setBalances] = useState({});
  const [settlements, setSettlements] = useState([]);
  const [showSettlementForm, setShowSettlementForm] = useState(false);
  const [members, setMembers] = useState([]);
  const [paidBy, setPaidBy] = useState("");
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [showTransactionDetails, setShowTransactionDetails] = useState(false);
  const [showCorrectionForm, setShowCorrectionForm] = useState(false);
  const [correctionDescription, setCorrectionDescription] = useState("");
  const [correctionPaidBy, setCorrectionPaidBy] = useState("");
  const [correctionSplits, setCorrectionSplits] = useState({});
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [splits, setSplits] = useState({});

  const userNames = Object.fromEntries(
    members.map((member) => [member.id, member.name])
  );

  const loadPreviousLedgers = async () => {
  if (!currentUserId) return;

  try {
    const response = await fetch(
      `${API_URL}/users/${currentUserId}/groups`
    );

    if (!response.ok) {
      throw new Error("Failed to load previous ledgers");
    }

    const data = await response.json();

    setPreviousLedgers(data);
  } catch (error) {
    console.error(
      "Error loading previous ledgers:",
      error
    );

    setErrorMessage(error.message);
  }
};


const handleOpenLedger = async (ledger) => {
  localStorage.setItem(
    GROUP_STORAGE_KEY,
    String(ledger.id)
  );

  setGroupId(String(ledger.id));
  setGroupName(ledger.name);
  setShowSetup(false);
  setLoading(true);
  setErrorMessage("");
};
  // ---------------------------------------------------------
  // Setup
  // ---------------------------------------------------------

  const handleSetupMemberChange = (index, field, value) => {
    setSetupMembers((current) =>
      current.map((member, memberIndex) =>
        memberIndex === index
          ? { ...member, [field]: value }
          : member
      )
    );
  };

  const addSetupMember = () => {
    setSetupMembers((current) => [
      ...current,
      { name: "", email: "" },
    ]);
  };

  const removeSetupMember = (index) => {
    setSetupMembers((current) =>
      current.filter((_, memberIndex) => memberIndex !== index)
    );
  };

  const handleCreateLedger = async () => {
    if (actionLoading === "setup") return;

    const name = setupName.trim();
    const email = setupEmail.trim();
    const ledgerName = setupGroupName.trim();

    if (!name || !email || !ledgerName) {
      setErrorMessage(
        "Your name, email, and group name are required."
      );
      return;
    }

    const validMembers = setupMembers
      .map((member) => ({
        name: member.name.trim(),
        email: member.email.trim(),
      }))
      .filter((member) => member.name || member.email);

    const incompleteMember = validMembers.find(
      (member) => !member.name || !member.email
    );

    if (incompleteMember) {
      setErrorMessage(
        "Every member must have both a name and an email."
      );
      return;
    }

    const emails = [
      email.toLowerCase(),
      ...validMembers.map((member) => member.email.toLowerCase()),
    ];

    if (new Set(emails).size !== emails.length) {
      setErrorMessage("Each user must have a unique email.");
      return;
    }

    try {
      setActionLoading("setup");
      setErrorMessage("");

      // -----------------------------------------------------
      // 1. Create current user
      // -----------------------------------------------------

      const userResponse = await fetch(`${API_URL}/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          email,
        }),
      });

      if (!userResponse.ok) {
        const error = await userResponse.json();
        throw new Error(
          error.detail || "Failed to create your user"
        );
      }

      const currentUser = await userResponse.json();

      // -----------------------------------------------------
      // 2. Create remaining users
      // -----------------------------------------------------

      const createdMembers = [];

      for (const member of validMembers) {
        const response = await fetch(`${API_URL}/users`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(member),
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(
            error.detail ||
              `Failed to create user ${member.name}`
          );
        }

        const createdUser = await response.json();
        createdMembers.push(createdUser);
      }

      // -----------------------------------------------------
      // 3. Create group
      // -----------------------------------------------------

      const groupResponse = await fetch(`${API_URL}/groups`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: ledgerName,
          created_by: currentUser.id,
        }),
      });

      if (!groupResponse.ok) {
        const error = await groupResponse.json();
        throw new Error(
          error.detail || "Failed to create group"
        );
      }

      const group = await groupResponse.json();

      // -----------------------------------------------------
      // 4. Add members to group
      // -----------------------------------------------------

      for (const member of createdMembers) {
        const response = await fetch(
          `${API_URL}/groups/${group.id}/members`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              user_id: member.id,
            }),
          }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(
            error.detail ||
              `Failed to add ${member.name} to the group`
          );
        }
      }

      // -----------------------------------------------------
      // 5. Persist current group/user
      // -----------------------------------------------------

      localStorage.setItem(
        GROUP_STORAGE_KEY,
        String(group.id)
      );

      localStorage.setItem(
        USER_STORAGE_KEY,
        String(currentUser.id)
      );

      setGroupId(String(group.id));
      setCurrentUserId(String(currentUser.id));
      setGroupName(group.name || ledgerName);

      setShowSetup(false);
      setLoading(true);
    } catch (error) {
      console.error("Error creating ledger:", error);
      setErrorMessage(error.message);
    } finally {
      setActionLoading("");
    }
  };

  // ---------------------------------------------------------
  // Load members / group
  // ---------------------------------------------------------

  const loadMembers = async () => {
    if (!groupId) return [];

    try {
      const response = await fetch(
        `${API_URL}/groups/${groupId}`
      );

      if (!response.ok) {
        throw new Error("Failed to load group");
      }

      const data = await response.json();

      setMembers(data.members || []);
      setGroupName(data.name || "Expense Ledger");

      const memberSplits = Object.fromEntries(
        (data.members || []).map((member) => [
          member.id,
          "",
        ])
      );

      setSplits(memberSplits);

      // Default payer to current user if they are a member.
      // Otherwise use the first member.
      const currentMember = (data.members || []).find(
        (member) =>
          String(member.id) === String(currentUserId)
      );

      const defaultUser =
        currentMember?.id || data.members?.[0]?.id || "";

      setPaidBy(defaultUser);
      setCorrectionPaidBy(defaultUser);

      return data.members || [];
    } catch (error) {
      console.error("Error loading members:", error);
      setErrorMessage(error.message);
      return [];
    }
  };

  // ---------------------------------------------------------
  // Load transactions
  // ---------------------------------------------------------

  const loadTransactions = async (memberList = members) => {
    if (!groupId) return;

    try {
      const response = await fetch(
        `${API_URL}/groups/${groupId}/transactions`
      );

      if (!response.ok) {
        throw new Error("Failed to load transactions");
      }

      const data = await response.json();

      const names = Object.fromEntries(
        memberList.map((member) => [
          member.id,
          member.name,
        ])
      );

      setTransactions(
        data.map((transaction) => ({
          id: transaction.id,
          description: transaction.description,
          paidBy:
            names[transaction.paid_by] || "Unknown",
          amount: Number(transaction.amount),
          date: new Date(
            transaction.created_at
          ).toLocaleDateString("en-IN", {
            day: "2-digit",
            month: "short",
          }),
          settlement:
            transaction.transaction_type ===
            "SETTLEMENT",
          reversal:
            transaction.transaction_type ===
            "REVERSAL",
        }))
      );
    } catch (error) {
      console.error("Error loading transactions:", error);
      setErrorMessage(error.message);
    }
  };

  // ---------------------------------------------------------
  // Load balances
  // ---------------------------------------------------------

  const loadBalances = async () => {
    if (!groupId) return;

    try {
      const response = await fetch(
        `${API_URL}/groups/${groupId}/balances`
      );

      if (!response.ok) {
        throw new Error("Failed to load balances");
      }

      const data = await response.json();

      setBalances(data);
    } catch (error) {
      console.error("Error loading balances:", error);
      setErrorMessage(error.message);
    }
  };

  // ---------------------------------------------------------
  // Load settlement suggestions
  // ---------------------------------------------------------

  const loadSettlements = async () => {
    if (!groupId) return;

    try {
      const response = await fetch(
        `${API_URL}/groups/${groupId}/settlements`
      );

      if (!response.ok) {
        throw new Error("Failed to load settlements");
      }

      const data = await response.json();

      setSettlements(data);
    } catch (error) {
      console.error("Error loading settlements:", error);
      setErrorMessage(error.message);
    }
  };

  // ---------------------------------------------------------
  // Load transaction details
  // ---------------------------------------------------------

  const loadTransactionDetails = async (transactionId) => {
    try {
      const response = await fetch(
        `${API_URL}/transactions/${transactionId}`
      );

      if (!response.ok) {
        throw new Error("Failed to load transaction");
      }

      const data = await response.json();

      setSelectedTransaction(data);
      setShowTransactionDetails(true);
    } catch (error) {
      console.error(
        "Error loading transaction details:",
        error
      );
      setErrorMessage(error.message);
    }
  };

  // ---------------------------------------------------------
  // Open correction form
  // ---------------------------------------------------------

  const openCorrectionForm = () => {
    if (!selectedTransaction) return;

    const payerEntry = selectedTransaction.entries.find(
      (entry) => Number(entry.amount) > 0
    );

    const correctionSplitValues = Object.fromEntries(
      selectedTransaction.entries
        .filter((entry) => Number(entry.amount) < 0)
        .map((entry) => [
          entry.user_id,
          Math.abs(Number(entry.amount)).toString(),
        ])
    );

    setCorrectionDescription(
      selectedTransaction.description
    );

    setCorrectionPaidBy(
      payerEntry?.user_id ||
        currentUserId ||
        members[0]?.id ||
        ""
    );

    setCorrectionSplits(correctionSplitValues);

    setShowTransactionDetails(false);
    setShowCorrectionForm(true);
  };

  // ---------------------------------------------------------
  // Correct expense
  // ---------------------------------------------------------

  const handleCorrectExpense = async () => {
    if (
      !selectedTransaction ||
      !isValidCorrection ||
      actionLoading
    ) {
      return;
    }

    const correctionSplitData = Object.fromEntries(
      members.map((member) => [
        member.id,
        Number(correctionSplits[member.id] || 0),
      ])
    );

    try {
      setActionLoading("correction");
      setErrorMessage("");

      const response = await fetch(
        `${API_URL}/transactions/${selectedTransaction.id}/correct`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            description: correctionDescription.trim(),
            created_by: Number(currentUserId),
            paid_by: Number(correctionPaidBy),
            splits: correctionSplitData,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();

        throw new Error(
          error.detail || "Failed to correct expense"
        );
      }

      await response.json();

      await loadTransactions(members);
      await loadBalances();
      await loadSettlements();

      setShowCorrectionForm(false);
      setSelectedTransaction(null);
      setCorrectionDescription("");
      setCorrectionSplits({});
    } catch (error) {
      console.error("Error correcting expense:", error);
      setErrorMessage(error.message);
    } finally {
      setActionLoading("");
    }
  };

  // ---------------------------------------------------------
  // Initial dashboard load
  // ---------------------------------------------------------

  useEffect(() => {
    if (!groupId || showSetup) {
      setLoading(false);
      return;
    }

    const loadData = async () => {
      setLoading(true);
      setErrorMessage("");

      try {
        const memberList = await loadMembers();

        await Promise.all([
          loadTransactions(memberList),
          loadBalances(),
          loadSettlements(),
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [groupId, showSetup]);

  // ---------------------------------------------------------
  // Expense calculations
  // ---------------------------------------------------------

  const splitTotal = Object.values(splits).reduce(
    (total, amount) =>
      total + Number(amount || 0),
    0
  );

  const handleAddExpense = async () => {
    if (!isValidSplit || actionLoading) return;

    const expense = {
      description: description.trim(),
      created_by: Number(currentUserId),
      paid_by: Number(paidBy),
      splits: Object.fromEntries(
        members.map((member) => [
          member.id,
          Number(splits[member.id] || 0),
        ])
      ),
    };

    try {
      setActionLoading("expense");
      setErrorMessage("");

      const response = await fetch(
        `${API_URL}/groups/${groupId}/expenses`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(expense),
        }
      );

      if (!response.ok) {
        const error = await response.json();

        throw new Error(
          error.detail || "Failed to add expense"
        );
      }

      await response.json();

      await loadTransactions(members);
      await loadBalances();
      await loadSettlements();

      setDescription("");

      setSplits(
        Object.fromEntries(
          members.map((member) => [member.id, ""])
        )
      );

      setShowExpenseForm(false);
    } catch (error) {
      console.error("Error adding expense:", error);
      setErrorMessage(error.message);
    } finally {
      setActionLoading("");
    }
  };

  // ---------------------------------------------------------
  // Settlement
  // ---------------------------------------------------------

  const handleSettlement = async (settlement) => {
    try {
      setActionLoading("settlement");
      setErrorMessage("");

      const response = await fetch(
        `${API_URL}/groups/${groupId}/settlements`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from_user: settlement.from_user,
            to_user: settlement.to_user,
            amount: settlement.amount,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();

        throw new Error(
          error.detail || "Failed to create settlement"
        );
      }

      await response.json();

      await loadBalances();
      await loadSettlements();
      await loadTransactions(members);
    } catch (error) {
      console.error(
        "Error creating settlement:",
        error
      );
      setErrorMessage(error.message);
    } finally {
      setActionLoading("");
    }
  };

  // ---------------------------------------------------------
  // Validation
  // ---------------------------------------------------------

  const isValidSplit =
    description.trim().length > 0 &&
    splitTotal > 0 &&
    paidBy &&
    Object.values(splits).every(
      (amount) => Number(amount || 0) >= 0
    );

  const correctionTotal = Object.values(
    correctionSplits
  ).reduce(
    (total, amount) =>
      total + Number(amount || 0),
    0
  );

  const isValidCorrection =
    correctionDescription.trim().length > 0 &&
    correctionTotal > 0 &&
    correctionPaidBy &&
    Object.values(correctionSplits).every(
      (amount) => Number(amount || 0) >= 0
    );

  // ---------------------------------------------------------
  // Load previous ledgers when setup screen is visible
  // ---------------------------------------------------------

  useEffect(() => {
    if (showSetup && currentUserId) {
      loadPreviousLedgers();
    }
  }, [showSetup, currentUserId]);

  // ---------------------------------------------------------
  // Setup screen
  // ---------------------------------------------------------

  if (showSetup) {
  return (
    <CreateLedger
      previousLedgers={previousLedgers}
      handleOpenLedger={handleOpenLedger}
      setupName={setupName}
      setupEmail={setupEmail}
      setupGroupName={setupGroupName}
      setupMembers={setupMembers}
      actionLoading={actionLoading}
      errorMessage={errorMessage}

      setSetupName={setSetupName}
      setSetupEmail={setSetupEmail}
      setSetupGroupName={setSetupGroupName}

      handleSetupMemberChange={handleSetupMemberChange}
      addSetupMember={addSetupMember}
      removeSetupMember={removeSetupMember}
      handleCreateLedger={handleCreateLedger}
    />
  );
}

  // ---------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------

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
                          balance >= 0
                            ? "positive"
                            : "negative"
                        }`}
                      >
                        {balance > 0
                          ? "+ "
                          : balance < 0
                            ? "- "
                            : ""}
                        ₹
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
    onClick={() => {
      setErrorMessage("");
      setShowExpenseForm(true);
    }}
  >
    + Add Expense
  </button>

  <button
    className="action-button secondary"
    onClick={() => {
      setErrorMessage("");
      setShowSettlementForm(true);
    }}
  >
    Settle Up →
  </button>

  <button
    className="action-button secondary"
    onClick={() => {
      setErrorMessage("");
      setShowSetup(true);
      loadPreviousLedgers();
    }}
  >
    Create Ledger →
  </button>
</section>

            {/* -------------------------------------------------
                TRANSACTIONS
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
                  <div className="modal-placeholder">
                    No transactions yet.
                  </div>
                ) : (
                  transactions.map((transaction) => (
                    <div
                      className="transaction-row"
                      key={transaction.id}
                      onClick={() =>
                        loadTransactionDetails(
                          transaction.id
                        )
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
                        ₹
                        {transaction.amount.toFixed(
                          2
                        )}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}
      </main>

      {/* =====================================================
          ADD EXPENSE
      ===================================================== */}

      {showExpenseForm && (
        <div className="modal-overlay">
          <div className="expense-modal">
            <div className="modal-header">
              <div>
                <p className="eyebrow">
                  NEW ENTRY / 03
                </p>

                <h2>Add Expense</h2>
              </div>

              <button
                className="modal-close"
                onClick={() =>
                  setShowExpenseForm(false)
                }
              >
                ×
              </button>
            </div>

            <div className="expense-form">
              <label>
                Description

                <input
                  type="text"
                  placeholder="e.g. Dinner"
                  value={description}
                  onChange={(e) =>
                    setDescription(e.target.value)
                  }
                />
              </label>

              <label>
                Amount

                <input
                  type="number"
                  value={splitTotal.toFixed(2)}
                  readOnly
                />
              </label>

              <label>
                Paid by

                <select
                  value={paidBy}
                  onChange={(e) =>
                    setPaidBy(Number(e.target.value))
                  }
                >
                  {members.map((member) => (
                    <option
                      key={member.id}
                      value={member.id}
                    >
                      {member.name}
                    </option>
                  ))}
                </select>
              </label>

              <div className="split-section">
                <div className="split-header">
                  <span>SPLIT BETWEEN</span>
                  <span>AMOUNT</span>
                </div>

                {members.map((member) => (
                  <div
                    className="split-row"
                    key={member.id}
                  >
                    <label>{member.name}</label>

                    <input
                      type="number"
                      min="0"
                      value={splits[member.id] || ""}
                      onChange={(e) =>
                        setSplits({
                          ...splits,
                          [member.id]:
                            e.target.value,
                        })
                      }
                      placeholder="0.00"
                    />
                  </div>
                ))}

                <button
                  className="action-button primary"
                  disabled={
                    !isValidSplit ||
                    Boolean(actionLoading)
                  }
                  onClick={handleAddExpense}
                >
                  {actionLoading === "expense"
                    ? "Saving..."
                    : "Save Expense"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =====================================================
          SETTLEMENT
      ===================================================== */}

      {showSettlementForm && (
        <div className="modal-overlay">
          <div className="expense-modal">
            <div className="modal-header">
              <div>
                <p className="eyebrow">
                  SETTLEMENT / 04
                </p>

                <h2>Settle Up</h2>
              </div>

              <button
                className="modal-close"
                onClick={() =>
                  setShowSettlementForm(false)
                }
              >
                ×
              </button>
            </div>

            <div className="settlement-list">
              {settlements.length === 0 ? (
                <p className="modal-placeholder">
                  Everyone is settled up.
                </p>
              ) : (
                settlements.map(
                  (settlement, index) => (
                    <div
                      className="settlement-row"
                      key={index}
                    >
                      <div>
                        <span className="settlement-users">
                          {
                            userNames[
                              settlement.from_user
                            ]
                          }{" "}
                          →{" "}
                          {
                            userNames[
                              settlement.to_user
                            ]
                          }
                        </span>

                        <span className="transaction-meta">
                          Suggested settlement
                        </span>
                      </div>

                      <span className="amount positive mono">
                        ₹
                        {Number(
                          settlement.amount
                        ).toFixed(2)}
                      </span>

                      <button
                        className="action-button secondary"
                        disabled={
                          actionLoading ===
                          "settlement"
                        }
                        onClick={() =>
                          handleSettlement(
                            settlement
                          )
                        }
                      >
                        {actionLoading ===
                        "settlement"
                          ? "Saving..."
                          : "Confirm"}
                      </button>
                    </div>
                  )
                )
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================
          TRANSACTION DETAILS
      ===================================================== */}

      {showTransactionDetails &&
        selectedTransaction && (
          <div className="modal-overlay">
            <div className="expense-modal">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">
                    LEDGER ENTRY / 05
                  </p>

                  <h2>
                    {selectedTransaction.description}
                  </h2>
                </div>

                <div className="modal-header-actions">
                  {selectedTransaction.transaction_type ===
                    "EXPENSE" && (
                    <button
                      className="action-button secondary"
                      onClick={openCorrectionForm}
                    >
                      Correct
                    </button>
                  )}

                  <button
                    className="modal-close"
                    onClick={() => {
                      setShowTransactionDetails(
                        false
                      );
                      setSelectedTransaction(null);
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>

              <div className="transaction-details">
                <div className="detail-summary">
                  <span className="transaction-meta">
                    {
                      selectedTransaction.transaction_type
                    }
                  </span>

                  <span className="amount positive mono">
                    ₹
                    {Number(
                      selectedTransaction.amount
                    ).toFixed(2)}
                  </span>
                </div>

                <div className="detail-section">
                  <div className="split-header">
                    <span>LEDGER ENTRIES</span>
                    <span>AMOUNT</span>
                  </div>

                  {selectedTransaction.entries.map(
                    (entry, index) => (
                      <div
                        className="split-row"
                        key={`${entry.user_id}-${index}`}
                      >
                        <label>
                          {userNames[
                            entry.user_id
                          ] ||
                            `User ${entry.user_id}`}
                        </label>

                        <span
                          className={`mono ${
                            Number(entry.amount) >= 0
                              ? "positive"
                              : "negative"
                          }`}
                        >
                          {Number(entry.amount) >= 0
                            ? "+"
                            : "-"}{" "}
                          ₹
                          {Math.abs(
                            Number(entry.amount)
                          ).toFixed(2)}
                        </span>
                      </div>
                    )
                  )}
                </div>

                <div className="transaction-meta">
                  Created by{" "}
                  {userNames[
                    selectedTransaction.created_by
                  ] ||
                    `User ${selectedTransaction.created_by}`}
                </div>
              </div>
            </div>
          </div>
        )}

      {/* =====================================================
          CORRECT EXPENSE
      ===================================================== */}

      {showCorrectionForm &&
        selectedTransaction && (
          <div className="modal-overlay">
            <div className="expense-modal">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">
                    CORRECTION / 06
                  </p>

                  <h2>Correct Expense</h2>
                </div>

                <button
                  className="modal-close"
                  onClick={() =>
                    setShowCorrectionForm(false)
                  }
                >
                  ×
                </button>
              </div>

              <div className="expense-form">
                <label>
                  Description

                  <input
                    type="text"
                    value={correctionDescription}
                    onChange={(e) =>
                      setCorrectionDescription(
                        e.target.value
                      )
                    }
                  />
                </label>

                <label>
                  Amount

                  <input
                    type="number"
                    value={correctionTotal.toFixed(
                      2
                    )}
                    readOnly
                  />
                </label>

                <label>
                  Paid by

                  <select
                    value={correctionPaidBy}
                    onChange={(e) =>
                      setCorrectionPaidBy(
                        Number(e.target.value)
                      )
                    }
                  >
                    {members.map((member) => (
                      <option
                        key={member.id}
                        value={member.id}
                      >
                        {member.name}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="split-section">
                  <div className="split-header">
                    <span>SPLIT BETWEEN</span>
                    <span>AMOUNT</span>
                  </div>

                  {members.map((member) => (
                    <div
                      className="split-row"
                      key={member.id}
                    >
                      <label>{member.name}</label>

                      <input
                        type="number"
                        min="0"
                        value={
                          correctionSplits[
                            member.id
                          ] || ""
                        }
                        onChange={(e) =>
                          setCorrectionSplits({
                            ...correctionSplits,
                            [member.id]:
                              e.target.value,
                          })
                        }
                        placeholder="0.00"
                      />
                    </div>
                  ))}

                  <button
                    className="action-button primary"
                    disabled={
                      !isValidCorrection ||
                      Boolean(actionLoading)
                    }
                    onClick={
                      handleCorrectExpense
                    }
                  >
                    {actionLoading ===
                    "correction"
                      ? "Saving..."
                      : "Save Correction"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
    </div>
  );
}

export default App;