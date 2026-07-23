import { useState, useRef, useEffect } from 'react';

const API_BASE = 'http://localhost:5000/api';

export default function ChatWidget({ venueId, venueName = "MuseBot" }) {
  const [authToken, setAuthToken] = useState(null);
  const [authEmail, setAuthEmail] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [authStep, setAuthStep] = useState('email');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  const [language, setLanguage] = useState('en');
  const LANGUAGES = { en: 'English', hi: 'Hindi', mr: 'Marathi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali', gu: 'Gujarati', kn: 'Kannada' };

  const [formExhibits, setFormExhibits] = useState([]);
  const [formData, setFormData] = useState({
    exhibitId: '',
    adults: 1,
    kids: 0,
    date: ''
  });

  const [messages, setMessages] = useState([
    { sender: 'bot', text: `Hi! Say 'hi' to start booking your tickets for ${venueName} 🎟️` }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const requestOtp = async () => {
    if (!authEmail.trim()) return;
    setAuthLoading(true);
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/auth/request-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail.trim() })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to send OTP');
      }
      setAuthStep('otp');
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const verifyOtp = async () => {
    if (!otpInput.trim()) return;
    setAuthLoading(true);
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail.trim(), otp: otpInput.trim() })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Invalid OTP');
      }
      const data = await res.json();
      setAuthToken(data.access_token);
      setAuthStep('done');
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const changeLanguage = async (lang) => {
    setLanguage(lang);
    await fetch(`${API_BASE}/chat/set-language`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
      body: JSON.stringify({ language: lang })
    });
  };

  const startNewConversation = async () => {
    await fetch(`${API_BASE}/chat/reset`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    setMessages([{ sender: 'bot', text: `Hi! Say 'hi' to start booking your tickets for ${venueName} 🎟️` }]);
  };

  const submitRating = async (bookingId, rating, messageIndex) => {
    try {
      await fetch(`${API_BASE}/bookings/${bookingId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating })
      });
      setMessages(prev => prev.map((m, i) =>
        i === messageIndex ? { ...m, showRating: false, ratedValue: rating } : m
      ));
    } catch (err) {
      console.error('Rating failed', err);
    }
  };

  const openRazorpayCheckout = (order, bookingId) => {
    const options = {
      key: order.razorpay_key_id,
      amount: order.amount * 100,
      currency: order.currency,
      name: venueName,
      description: "Ticket Booking",
      order_id: order.order_id,
      handler: async function (response) {
        try {
          const verifyRes = await fetch(`${API_BASE}/payment/verify`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
              booking_id: bookingId,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            })
          });
          const verifyData = await verifyRes.json();

          if (!verifyRes.ok) {
            setMessages(prev => [...prev, { sender: 'bot', text: 'Payment verification failed. Please try again.' }]);
            return;
          }

          setMessages(prev => [...prev, {
            sender: 'bot',
            text: verifyData.message || '🎉 Payment successful!',
            qr_code: verifyData.qr_code,
            showRating: verifyData.show_rating,
            bookingId: bookingId
          }]);
        } catch (err) {
          setMessages(prev => [...prev, { sender: 'bot', text: 'Payment verification failed. Please try again.' }]);
        }
      },
      modal: {
        ondismiss: function () {
          setMessages(prev => [...prev, { sender: 'bot', text: 'Payment cancelled. Say "yes" again when ready to pay.' }]);
        }
      },
      theme: { color: "#4F46E5" }
    };
    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const sendMessage = async (overrideMessage) => {
    const userMsg = (overrideMessage ?? input).trim();
    if (!userMsg || loading) return;
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ message: userMsg, venue_id: venueId })
      });

      if (res.status === 401) {
        setMessages(prev => [...prev, { sender: 'bot', text: 'Your session expired. Please log in again.' }]);
        setAuthToken(null);
        setAuthStep('email');
        return;
      }

      const data = await res.json();
      setMessages(prev => [...prev, { sender: 'bot', text: data.reply, qr_code: data.qr_code, showBookingForm: data.show_booking_form }]);

      if (data.show_booking_form) {
        const res2 = await fetch(`${API_BASE}/exhibits/?venue_id=${venueId}`);
        const exhibits = await res2.json();
        setFormExhibits(exhibits);
        if (exhibits.length > 0) {
          setFormData(prev => ({ ...prev, exhibitId: exhibits[0]._id }));
        }
      }

      if (data.action === 'initiate_payment') {
        openRazorpayCheckout(data.order, data.booking_id);
      }
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'bot', text: 'Something went wrong. Try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  const submitBookingForm = () => {
    const exhibit = formExhibits.find(e => e._id === formData.exhibitId);
    if (!exhibit || !formData.date) return;
    const message = `${formData.adults} adults ${formData.kids} kid on ${formData.date} for ${exhibit.name}`;
    sendMessage(message);
  };

  const handleKeyDown = (e, action) => {
    if (e.key === 'Enter') action();
  };

  if (authStep !== 'done') {
    return (
      <div className="flex flex-col h-[600px] w-[380px] border rounded-xl shadow-lg bg-white">
        <div className="bg-indigo-600 text-white p-4 rounded-t-xl font-semibold">
          🎟️ {venueName}
        </div>
        <div className="flex-1 flex flex-col justify-center items-center p-6 gap-4">
          {authStep === 'email' && (
            <>
              <p className="text-sm text-gray-600 text-center">Enter your email to get started</p>
              <input
                type="email"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="you@example.com"
                value={authEmail}
                onChange={e => setAuthEmail(e.target.value)}
                onKeyDown={e => handleKeyDown(e, requestOtp)}
              />
              <button
                onClick={requestOtp}
                disabled={authLoading}
                className="w-full bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {authLoading ? 'Sending...' : 'Send Code'}
              </button>
            </>
          )}
          {authStep === 'otp' && (
            <>
              <p className="text-sm text-gray-600 text-center">Enter the code sent to {authEmail}</p>
              <input
                type="text"
                maxLength={6}
                className="w-full border rounded-lg px-3 py-2 text-sm text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="123456"
                value={otpInput}
                onChange={e => setOtpInput(e.target.value)}
                onKeyDown={e => handleKeyDown(e, verifyOtp)}
              />
              <button
                onClick={verifyOtp}
                disabled={authLoading}
                className="w-full bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {authLoading ? 'Verifying...' : 'Verify'}
              </button>
              <button
                onClick={() => { setAuthStep('email'); setAuthError(''); }}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Use a different email
              </button>
            </>
          )}
          {authError && <p className="text-xs text-red-500 text-center">{authError}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-[600px] w-[380px] border rounded-xl shadow-lg bg-white">
      <div className="bg-indigo-600 text-white p-4 rounded-t-xl font-semibold flex justify-between items-center">
        <span>🎟️ {venueName}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={startNewConversation}
            title="Start new conversation"
            className="text-xs text-blue-600 bg-white hover:bg-gray-100 rounded px-2 py-1"
          >
            ↻ New
          </button>
          <select
            value={language}
            onChange={e => changeLanguage(e.target.value)}
            className="text-xs text-indigo-900 rounded px-1 py-0.5"
          >
            {Object.entries(LANGUAGES).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-3 py-2 rounded-lg whitespace-pre-wrap text-sm ${
              m.sender === 'user' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-800'
            }`}>
              {m.text}
              {m.qr_code && (
                <img src={m.qr_code} alt="Ticket QR" className="mt-2 w-40 h-40" />
              )}
              {m.showBookingForm && formExhibits.length > 0 && (
                <div className="mt-3 bg-white border rounded-lg p-3">
                  <label className="text-xs text-gray-500 mb-1 block">Exhibit</label>
                  <select
                    value={formData.exhibitId}
                    onChange={e => setFormData({ ...formData, exhibitId: e.target.value })}
                    className="w-full border rounded-lg px-2 py-2 mb-3 text-sm"
                  >
                    {formExhibits.map(ex => (
                      <option key={ex._id} value={ex._id}>{ex.name} — ₹{ex.basePrice}</option>
                    ))}
                  </select>

                  <label className="text-xs text-gray-500 mb-1 block">Date</label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                    min={new Date().toISOString().split('T')[0]}
                    className="w-full border rounded-lg px-2 py-2 mb-3 text-sm"
                  />

                  <label className="text-xs text-gray-500 mb-1 block">Adults</label>
                  <div className="flex items-center gap-3 mb-3">
                    <button onClick={() => setFormData({ ...formData, adults: Math.max(1, formData.adults - 1) })} className="w-8 h-8 bg-gray-200 rounded-full font-bold">−</button>
                    <span className="w-6 text-center">{formData.adults}</span>
                    <button onClick={() => setFormData({ ...formData, adults: formData.adults + 1 })} className="w-8 h-8 bg-gray-200 rounded-full font-bold">+</button>
                  </div>

                  <label className="text-xs text-gray-500 mb-1 block">Children (under 12)</label>
                  <div className="flex items-center gap-3 mb-4">
                    <button onClick={() => setFormData({ ...formData, kids: Math.max(0, formData.kids - 1) })} className="w-8 h-8 bg-gray-200 rounded-full font-bold">−</button>
                    <span className="w-6 text-center">{formData.kids}</span>
                    <button onClick={() => setFormData({ ...formData, kids: formData.kids + 1 })} className="w-8 h-8 bg-gray-200 rounded-full font-bold">+</button>
                  </div>

                  <button onClick={submitBookingForm} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm font-medium">Continue</button>
                </div>
              )}
              {m.showRating && (
                <div className="mt-3 flex items-center gap-1">
                  <span className="text-xs text-gray-500 mr-1">Rate your visit:</span>
                  {[1, 2, 3, 4, 5].map(star => (
                    <button key={star} onClick={() => submitRating(m.bookingId, star, i)} className="text-xl hover:scale-110 transition-transform">⭐</button>
                  ))}
                </div>
              )}
              {m.ratedValue && (
                <p className="text-xs text-gray-500 mt-2">You rated: {'⭐'.repeat(m.ratedValue)}</p>
              )}
            </div>
          </div>
        ))}
        {loading && <div className="text-xs text-gray-400">Typing...</div>}
        <div ref={scrollRef} />
      </div>

      <div className="p-3 border-t flex gap-2">
        <input
          id="musebot-input"
          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Type your message..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => handleKeyDown(e, () => sendMessage())}
        />
        <button
          id="musebot-send-btn"
          onClick={() => sendMessage()}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          Send
        </button>
      </div>
    </div>
  );
}