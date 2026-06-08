import { useState } from "react";
import {
  Leaf,
  Send,
  Loader2,
  ShieldCheck,
  PackageSearch,
  Brain,
  AlertTriangle,
  Sprout,
  UserRound,
  Bot,
  Activity,
  CheckCircle2,
  ImagePlus, // <-- ADDED: Icon for the upload button
} from "lucide-react";
import "./App.css";

const API_URL = "http://localhost:8000/chat";
const DIAGNOSE_URL = "http://localhost:8000/diagnose";// <-- ADDED: Image endpoint

const examples = [
  "My tomato leaves have yellow spots. What should I use?",
  "My child touched pesticide and his skin is burning",
  "Can you recommend a product for tomato aphids?",
  "Where is my order?",
  "Where is my order 1001?",
  "I have a complaint. The product arrived damaged and I want a refund",
];

function formatLabel(value) {
  if (!value) return "Not available";
  return value.replaceAll("_", " ");
}

function App() {
  const [customerId, setCustomerId] = useState("C001");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [latestResult, setLatestResult] = useState(null);

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Hello, I’m Agro-Mind. Describe your crop issue, upload a photo of your plant, or ask a support question.",
    },
  ]);

  // ==========================================
  // EXISTING: SEND TEXT MESSAGE
  // ==========================================
  async function sendMessage(customMessage = null) {
    const textToSend = customMessage || message;

    if (!textToSend.trim()) return;

    const userMessage = {
      role: "user",
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMessage]);
    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_id: customerId,
          message: textToSend,
        }),
      });

      if (!response.ok) {
        throw new Error("Backend returned an error");
      }

      const data = await response.json();
      setLatestResult(data);

      const assistantMessage = {
        role: "assistant",
        text: buildFriendlyResponse(data),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        error: true,
        text:
          "I couldn’t connect to the Agro-Mind backend. Make sure FastAPI is running on http://127.0.0.1:8000.",
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  // ==========================================
  // NEW: HANDLE IMAGE UPLOAD
  // ==========================================
  async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Reset input so you can upload the same file again if needed
    event.target.value = null;

    // Add a placeholder message to the chat
    const userMessage = {
      role: "user",
      text: `[Uploaded Image: ${file.name}]`,
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(DIAGNOSE_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Backend returned an error");
      }

      const data = await response.json();
      
      // Format the python tool's response into text
      let responseText = `📷 Image Diagnosis Complete:\n\n`;
      responseText += `Condition: ${data.disease} (Confidence: ${(data.confidence * 100).toFixed(0)}%)\n`;
      responseText += `Severity: ${data.severity}\n`;
      responseText += `Symptoms: ${data.symptoms?.join(", ")}\n\n`;
      responseText += `Recommendation: ${data.recommendation_hint}`;

      const assistantMessage = {
        role: "assistant",
        text: responseText,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      // Update the right panel with a custom layout for the image result
      setLatestResult({
        intent: "image_diagnosis",
        risk_level: data.severity === "high" ? "high" : "low",
        detected_crop: "From Image",
        detected_issue: data.disease,
        product_reason: data.recommendation_hint,
        escalation_required: data.confidence < 0.6,
      });

    } catch (error) {
      const errorMessage = {
        role: "assistant",
        error: true,
        text:
          "I couldn’t analyze the image. Make sure the backend is running and python-multipart is installed.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  function buildFriendlyResponse(data) {
    let response = "";

    if (data.intent === "order_status") {
      if (data.order?.order_found) {
        response += `I found the order details.\n\n`;
        response += `Order ID: ${data.order.order_id}\n`;
        response += `Status: ${data.order.status}\n`;
        response += `ETA: ${data.order.eta}\n`;
        response += `Tracking number: ${data.order.tracking_number}\n\n`;
        response += `${data.order.reason}`;
      } else {
        response += "I could not find an order for this request.\n\n";
        response += data.order?.reason || "No order information was available.";
      }

      if (data.case_saved) {
        response += `\n\nCase saved: Yes #${data.case_id}`;
      }

      return response;
    }

    if (data.intent === "pesticide_safety" || data.risk_level === "high") {
      response +=
        "This looks like a high-risk safety case. Please avoid giving treatment advice until a human expert reviews it.\n\n";
    }

    if (data.detected_crop || data.detected_issue) {
      response += `Possible crop: ${data.detected_crop || "Not detected"}\n`;
      response += `Possible issue: ${data.detected_issue || "Not confirmed"}\n\n`;
    }

    if (data.recommended_product) {
      response += `Suggested product: ${data.recommended_product}\n`;
      response +=
        "Please confirm the diagnosis before applying any pesticide or treatment.\n\n";
    } else {
      response += "No product recommendation was made for this message.\n\n";
    }

    response += `Risk level: ${data.risk_level}\n`;
    response += data.escalation_required
      ? "Escalation: Human expert review is recommended."
      : "Escalation: No human escalation needed right now.";

    if (data.case_saved) {
      response += `\nCase saved: Yes #${data.case_id}`;
    }

    return response;
  }

  const riskLevel = latestResult?.risk_level || "none";
  const isOrderStatus = latestResult?.intent === "order_status";

  return (
    <div className="app-shell">
      <div className="glow glow-one"></div>
      <div className="glow glow-two"></div>

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Leaf size={22} />
          </div>
          <div>
            <h1>Agro-Mind</h1>
            <p>AI Agricultural Support Assistant</p>
          </div>
        </div>

        <div className="system-status">
          <span></span>
          Live agent pipeline
        </div>
      </header>

      <main className="main-layout">
        <section className="chat-card">
          <div className="chat-header">
            <div>
              <div className="eyebrow">
                <Sprout size={15} />
                Customer Chat
              </div>
              <h2>Ask Agro-Mind</h2>
              <p>
                Chat with the support agent. The backend analyzes each message
                using intent detection, safety checks, product matching, order
                lookup, and case memory.
              </p>
            </div>
            <Bot size={34} />
          </div>

          <div className="customer-row">
            <label>Customer ID</label>
            <input
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="C001"
            />
          </div>

          <div className="chat-window">
            {messages.map((item, index) => (
              <div
                key={index}
                className={`message-row ${
                  item.role === "user" ? "user-row" : "assistant-row"
                }`}
              >
                <div className="message-avatar">
                  {item.role === "user" ? (
                    <UserRound size={17} />
                  ) : (
                    <Leaf size={17} />
                  )}
                </div>

                <div
                  className={`message-bubble ${
                    item.role === "user" ? "user-bubble" : "assistant-bubble"
                  } ${item.error ? "error-bubble" : ""}`}
                >
                  <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: 0 }}>
                    {item.text}
                  </pre>
                </div>
              </div>
            ))}

            {loading && (
              <div className="message-row assistant-row">
                <div className="message-avatar">
                  <Leaf size={17} />
                </div>
                <div className="message-bubble assistant-bubble typing">
                  <Loader2 className="spin" size={16} />
                  Analyzing...
                </div>
              </div>
            )}
          </div>

          <div className="examples">
            {examples.map((example) => (
              <button
                key={example}
                onClick={() => sendMessage(example)}
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>

          <div className="composer" style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            
            {/* NEW: IMAGE UPLOAD BUTTON */}
            <label 
              style={{ cursor: loading ? "not-allowed" : "pointer", padding: "8px", opacity: loading ? 0.5 : 1 }} 
              title="Upload crop image"
            >
              <ImagePlus size={24} color="#666" />
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                disabled={loading}
                style={{ display: "none" }}
              />
            </label>

            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type a customer message..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              style={{ flex: 1 }}
            />
            <button onClick={() => sendMessage()} disabled={loading}>
              {loading ? (
                <Loader2 className="spin" size={19} />
              ) : (
                <Send size={19} />
              )}
            </button>
          </div>
        </section>

        <aside className="agent-panel">
          <div className="panel-header">
            <div>
              <p>Agent Analysis</p>
              <h3>
                {latestResult ? formatLabel(latestResult.intent) : "No case yet"}
              </h3>
            </div>
            <span className={`risk-badge ${riskLevel}`}>{riskLevel}</span>
          </div>

          {!latestResult && (
            <div className="empty-panel">
              <Brain size={42} />
              <h3>Waiting for a message</h3>
              <p>
                Once a customer sends a message or uploads an image, the agent’s decision path will
                appear here.
              </p>
            </div>
          )}

          {latestResult && (
            <>
              <div className="metric-grid">
                <div className="metric-card">
                  <Brain size={21} />
                  <span>Intent</span>
                  <strong>{formatLabel(latestResult.intent)}</strong>
                </div>

                <div className="metric-card">
                  <ShieldCheck size={21} />
                  <span>Risk</span>
                  <strong>{latestResult.risk_level}</strong>
                </div>

                {latestResult.intent !== "image_diagnosis" && (
                  <div className="metric-card">
                    <CheckCircle2 size={21} />
                    <span>Case saved</span>
                    <strong>
                      {latestResult.case_saved
                        ? `Yes #${latestResult.case_id}`
                        : "Not saved"}
                    </strong>
                  </div>
                )}

                {isOrderStatus ? (
                  <>
                    <div className="metric-card">
                      <PackageSearch size={21} />
                      <span>Order ID</span>
                      <strong>{latestResult.order?.order_id || "Not found"}</strong>
                    </div>

                    <div className="metric-card">
                      <Activity size={21} />
                      <span>Status</span>
                      <strong>
                        {latestResult.order?.status || "Not available"}
                      </strong>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="metric-card">
                      <PackageSearch size={21} />
                      <span>Product/Crop</span>
                      <strong>{latestResult.recommended_product || latestResult.detected_crop || "None"}</strong>
                    </div>

                    <div className="metric-card">
                      <Activity size={21} />
                      <span>Escalation</span>
                      <strong>
                        {latestResult.escalation_required
                          ? "Required"
                          : "Not required"}
                      </strong>
                    </div>
                  </>
                )}
              </div>

              <div className="decision-card">
                <div className="decision-title">
                  <CheckCircle2 size={18} />
                  Current decision
                </div>

                {isOrderStatus ? (
                  <>
                    <p>
                      <strong>Order found:</strong>{" "}
                      {latestResult.order?.order_found ? "Yes" : "No"}
                    </p>
                    <p>
                      <strong>ETA:</strong>{" "}
                      {latestResult.order?.eta || "Not available"}
                    </p>
                    <p>
                      <strong>Tracking number:</strong>{" "}
                      {latestResult.order?.tracking_number || "Not available"}
                    </p>
                    <p>
                      <strong>Reason:</strong>{" "}
                      {latestResult.order?.reason ||
                        "No lookup reason available"}
                    </p>
                  </>
                ) : (
                  <>
                    <p>
                      <strong>Detected crop:</strong>{" "}
                      {latestResult.detected_crop || "Not detected"}
                    </p>
                    <p>
                      <strong>Detected issue:</strong>{" "}
                      {latestResult.detected_issue || "Not detected"}
                    </p>
                    <p>
                      <strong>Reason:</strong>{" "}
                      {latestResult.product_reason ||
                        "No product reason available"}
                    </p>
                  </>
                )}
              </div>

              {latestResult.risk_level === "high" && (
                <div className="warning-card">
                  <AlertTriangle size={20} />
                  <div>
                    <strong>High-risk case</strong>
                    <p>
                      This case should be escalated to a human expert before
                      giving further instructions.
                    </p>
                  </div>
                </div>
              )}

              <details className="json-card">
                <summary>Raw backend JSON</summary>
                <pre>{JSON.stringify(latestResult, null, 2)}</pre>
              </details>
            </>
          )}
        </aside>
      </main>
    </div>
  );
}

export default App;