import { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:5000/api";

export default function ChatWidget() {
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Hi! Say 'hi' to start booking your museum tickets 🏛️",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const userId = useRef("web_" + Math.random().toString(36).slice(2, 10));
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const openRazorpayCheckout = (order, bookingId) => {
    const options = {
      key: order.razorpay_key_id,
      amount: order.amount * 100,
      currency: order.currency,
      name: "MuseBot",
      description: "Museum Ticket Booking",
      order_id: order.order_id,
      handler: async function (response) {
        try {
          const verifyRes = await fetch(`${API_BASE}/payment/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              booking_id: bookingId,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });
          const verifyData = await verifyRes.json();

          if (!verifyRes.ok) {
            setMessages((prev) => [
              ...prev,
              {
                sender: "bot",
                text: "Payment verification failed. Please try again.",
              },
            ]);
            return;
          }

          const plan = verifyData.itinerary?.plan?.length
            ? "\n\n📍 Your Personalized Visit Plan:\n" +
              verifyData.itinerary.plan.map((s) => `• ${s}`).join("\n")
            : "";

          setMessages((prev) => [
            ...prev,
            {
              sender: "bot",
              text: `🎉 Payment successful! Your ticket is confirmed.${plan}\n\nHere's your QR code:`,
              qr_code: verifyData.qr_code,
            },
          ]);
        } catch (err) {
          setMessages((prev) => [
            ...prev,
            {
              sender: "bot",
              text: "Payment verification failed. Please try again.",
            },
          ]);
        }
      },
      modal: {
        ondismiss: function () {
          setMessages((prev) => [
            ...prev,
            {
              sender: "bot",
              text: 'Payment cancelled. Say "yes" again when ready to pay.',
            },
          ]);
        },
      },
      theme: { color: "#4F46E5" },
    };
    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setMessages((prev) => [...prev, { sender: "user", text: userMsg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId.current, message: userMsg }),
      });
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: data.reply, qr_code: data.qr_code },
      ]);

      if (data.action === "initiate_payment") {
        openRazorpayCheckout(data.order, data.booking_id);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Something went wrong. Try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="flex flex-col h-[600px] w-[380px] border rounded-xl shadow-lg bg-white">
      <div className="bg-indigo-600 text-white p-4 rounded-t-xl font-semibold">
        🏛️ MuseBot
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] px-3 py-2 rounded-lg whitespace-pre-wrap text-sm ${
                m.sender === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {m.text}
              {m.qr_code && (
                <img
                  src={m.qr_code}
                  alt="Ticket QR"
                  className="mt-2 w-40 h-40"
                />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-xs text-gray-400">MuseBot is typing...</div>
        )}
        <div ref={scrollRef} />
      </div>

      <div className="p-3 border-t flex gap-2">
        <input
          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={sendMessage}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          Send
        </button>
      </div>
    </div>
  );
}
