import { BrowserRouter, Routes, Route } from 'react-router-dom';
import VenuePage from './components/VenuePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/venue/:slug" element={<VenuePage />} />
        <Route path="*" element={<div className="min-h-screen flex items-center justify-center text-gray-500">Visit /venue/&lt;slug&gt; to open a venue's chatbot</div>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;