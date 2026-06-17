import { useEffect, useState } from "react";

function CustomerProfile() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/customers")
      .then((response) => response.json())
      .then((data) => {
        setCustomers(data);
        setLoading(false);
      })
      .catch((error) => {
        console.log(error);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "32px" }}>
        <h1>Customer Profiles</h1>
        <p>Loading customer profiles...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "32px", maxWidth: "1100px", margin: "0 auto" }}>
      <h1>Customer Profiles</h1>

      {customers.length === 0 && <p>No customer profiles found.</p>}

      {customers.map((customer) => (
        <div
          key={customer.customer_id}
          style={{
            border: "1px solid rgba(255,255,255,0.15)",
            background: "rgba(255,255,255,0.06)",
            padding: "18px",
            margin: "14px 0",
            borderRadius: "14px",
          }}
        >
          <h2>Customer {customer.customer_id}</h2>

          <p>
            <strong>Segment:</strong>{" "}
            {customer.customer_segment || "Regular"}
          </p>

          <p>
            <strong>Crops:</strong>{" "}
            {(customer.crops || []).join(", ") || "Not available"}
          </p>

          <p>
            <strong>Common issues:</strong>{" "}
            {(customer.common_issues || []).join(", ") || "Not available"}
          </p>

          <p>
            <strong>Recommended products:</strong>{" "}
            {(customer.recommended_products || []).join(", ") ||
              "Not available"}
          </p>

          <p>
            <strong>Orders:</strong>{" "}
            {(customer.orders || [])
              .map((order) => order.order_id)
              .filter(Boolean)
              .join(", ") || "No orders"}
          </p>

          <p>
            <strong>Complaints:</strong> {customer.complaints_count || 0}
          </p>

          <p>
            <strong>Escalations:</strong> {customer.escalations_count || 0}
          </p>

          <p>
            <strong>Preferred language:</strong>{" "}
            {customer.preferred_language || "Not set"}
          </p>

          <p>
            <strong>Last interaction:</strong>{" "}
            {customer.last_interaction || "Not available"}
          </p>

          <p>
            <strong>Summary:</strong>{" "}
            {customer.profile_summary || "No summary available."}
          </p>

          {customer.upsell_opportunity && (
            <b style={{ color: "#7ee787" }}>🚀 Upsell Opportunity</b>
          )}
        </div>
      ))}
    </div>
  );
}

export default CustomerProfile;