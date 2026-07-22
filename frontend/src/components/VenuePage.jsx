import { useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import ChatWidget from './ChatWidget';

const API_BASE = 'http://localhost:5000/api';

export default function VenuePage() {
  const { slug } = useParams();
  const [venue, setVenue] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVenue = async () => {
      try {
        const res = await fetch(`${API_BASE}/venues/slug/${slug}`);
        if (!res.ok) {
          throw new Error('Venue not found');
        }
        const data = await res.json();
        setVenue(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchVenue();
  }, [slug]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading...</div>;
  }

  if (error || !venue) {
    return <div className="min-h-screen flex items-center justify-center text-red-500">Venue not found: {slug}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <ChatWidget venueId={venue._id} venueName={venue.name} />
    </div>
  );
}