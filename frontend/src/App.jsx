import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Markdown from 'react-markdown';
import { Settings, UploadCloud, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';
import CalendarGrid from './CalendarGrid';
import './index.css';

const API_URL = 'https://floppascheduler.onrender.com';

function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [scrapeUrl, setScrapeUrl] = useState('https://anc.ca.apm.activecommunities.com/activewaterloo/activity/search?onlineSiteId=0&activity_select_param=2&activity_category_ids=35&viewMode=list');
  const [userIntent, setUserIntent] = useState('');
  const [fixedEvents, setFixedEvents] = useState([]);
  const [isParsing, setIsParsing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const fileInputRef = useRef(null);

  useEffect(() => {
    // Load state from local storage on mount
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) setApiKey(savedKey);
    else setShowSettings(true); // Prompt for key if not found

    const savedUrl = localStorage.getItem('scrape_url');
    if (savedUrl) setScrapeUrl(savedUrl);

    const savedEvents = localStorage.getItem('fixed_events');
    if (savedEvents) setFixedEvents(JSON.parse(savedEvents));
  }, []);

  const saveSettings = () => {
    localStorage.setItem('gemini_api_key', apiKey);
    localStorage.setItem('scrape_url', scrapeUrl);
    setShowSettings(false);
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!apiKey) {
      setError('Please configure your Gemini API Key in Settings first.');
      setShowSettings(true);
      return;
    }

    setIsParsing(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('gemini_api_key', apiKey);

    try {
      const res = await axios.post(`${API_URL}/parse_image`, formData);
      const events = res.data.events || [];
      setFixedEvents(events);
      localStorage.setItem('fixed_events', JSON.stringify(events));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to parse image');
    } finally {
      setIsParsing(false);
    }
  };

  const generateSchedule = async () => {
    if (!userIntent.trim()) return;
    if (!apiKey) {
      setShowSettings(true);
      return;
    }

    setIsGenerating(true);
    setError('');
    setResult(null);

    // Build the dynamic constraints object using the user's provided URL
    const constraints = {
      fixed_schedule: fixedEvents,
      venues: {
        ice_rink: {
          scrape_url: scrapeUrl,
          open_hours: { weekday: ["00:00-23:59"], weekend: ["00:00-23:59"] },
          reservation_required: true,
          reservation_advance_days: 1
        }
      }
    };

    try {
      const res = await axios.post(`${API_URL}/generate`, {
        user_intent: userIntent,
        constraints: constraints,
        gemini_api_key: apiKey
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate schedule');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="app-container">
      <header className="flex justify-between items-center mb-8">
        <h1>FloppaSchedule</h1>
        <button className="secondary flex items-center gap-2" onClick={() => setShowSettings(true)}>
          <Settings size={18} /> Settings
        </button>
      </header>

      {error && (
        <div className="glass-panel mb-4 flex items-center gap-2" style={{ borderColor: 'var(--error)' }}>
          <AlertCircle color="var(--error)" />
          <p style={{ margin: 0, color: 'var(--error)' }}>{error}</p>
        </div>
      )}

      <div className="flex flex-col gap-4 mb-8">
        <div className="glass-panel">
          <h2>1. Extract Fixed Schedule</h2>
          <p>Upload a screenshot of your calendar (Quest, Notion, etc.) to automatically extract fixed classes.</p>

          <div
            className="drop-zone mt-4"
            onClick={() => fileInputRef.current.click()}
          >
            <UploadCloud size={48} color={isParsing ? "var(--primary)" : "var(--text-muted)"} style={{ margin: '0 auto 1rem' }} />
            {isParsing ? <h3>Scanning Image with AI...</h3> : <h3>Click to upload screenshot</h3>}
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="image/*"
              onChange={handleImageUpload}
            />
          </div>

          {fixedEvents.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 flex items-center gap-2 text-success">
                <CheckCircle2 size={16} /> {fixedEvents.length} Events Extracted
              </h4>
              <div className="flex" style={{ flexWrap: 'wrap' }}>
                {fixedEvents.map((e, idx) => (
                  <span key={idx} className="tag">{e.event_name} ({e.day_of_week})</span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="glass-panel">
          <h2>2. Schedule Generation</h2>
          <p>Tell Floppa what you want to achieve this week.</p>
          <textarea
            rows="4"
            placeholder="e.g. Schedule 3 ice training sessions (50 mins each) and 4 study sessions for Grind 75..."
            value={userIntent}
            onChange={(e) => setUserIntent(e.target.value)}
          ></textarea>

          <button
            className="mt-4 flex items-center gap-2"
            style={{ width: '100%', justifyContent: 'center', padding: '1rem', fontSize: '1.2rem' }}
            onClick={generateSchedule}
            disabled={isGenerating || !userIntent.trim()}
          >
            <Sparkles /> {isGenerating ? 'Thinking...' : 'Generate Perfect Schedule'}
          </button>
        </div>

        {result && (
          <div className="glass-panel" id="result-view">
            <h2>Generated Schedule</h2>
            <div className="mt-4">
              {result.schedule_plan && result.schedule_plan.events ? (
                <CalendarGrid events={result.schedule_plan.events} />
              ) : (
                <p>No schedule generated or invalid format.</p>
              )}
            </div>
            {result.evaluation !== "No conflicts found." && (
              <div className="mt-4 p-4" style={{ background: 'rgba(244, 63, 94, 0.1)', borderRadius: '8px' }}>
                <h4>Conflict Warnings:</h4>
                <div className="markdown-body mt-2">
                  <Markdown>{result.evaluation}</Markdown>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {showSettings && (
        <div className="settings-modal">
          <div className="glass-panel settings-content">
            <h2>Configuration</h2>
            <p>Your API key and URLs are stored securely in your browser's LocalStorage.</p>
            <div className="flex-col gap-2 mt-4">
              <label>Gemini API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
              />
            </div>
            <div className="flex-col gap-2 mt-4">
              <label>Ice Rink Scraper URL</label>
              <input
                type="text"
                value={scrapeUrl}
                onChange={(e) => setScrapeUrl(e.target.value)}
                placeholder="https://anc.ca.apm..."
              />
            </div>
            <div className="flex justify-between mt-8">
              <button className="secondary" onClick={() => setShowSettings(false)}>Cancel</button>
              <button onClick={saveSettings}>Save Settings</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
