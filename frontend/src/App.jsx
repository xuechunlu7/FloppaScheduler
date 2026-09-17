import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Markdown from 'react-markdown';
import { Settings, UploadCloud, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';
import CalendarGrid from './CalendarGrid';
import './index.css';

// Automatically use local backend in development, Render backend in production
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : 'https://floppascheduler.onrender.com';

function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [sources, setSources] = useState([
    { url: 'https://anc.ca.apm.activecommunities.com/activewaterloo/activity/search?onlineSiteId=0&activity_select_param=2&activity_category_ids=35&viewMode=list', activity_filter: '' }
  ]);
  const [weekFilter, setWeekFilter] = useState('This Week');
  const [manualTimesText, setManualTimesText] = useState('');
  const [userIntent, setUserIntent] = useState('');
  const [fixedEvents, setFixedEvents] = useState([]);
  const [isParsing, setIsParsing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isFetchingTimes, setIsFetchingTimes] = useState(false);
  const [result, setResult] = useState(null);
  const [venueTimes, setVenueTimes] = useState(null);
  const [error, setError] = useState('');

  const fileInputRef = useRef(null);

  useEffect(() => {
    // Load state from local storage on mount
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) setApiKey(savedKey);
    else setShowSettings(true); // Prompt for key if not found

    const savedSources = localStorage.getItem('venue_sources');
    if (savedSources) setSources(JSON.parse(savedSources));

    const savedManual = localStorage.getItem('manual_times_text');
    if (savedManual) setManualTimesText(savedManual);

    const savedEvents = localStorage.getItem('fixed_events');
    if (savedEvents) setFixedEvents(JSON.parse(savedEvents));
  }, []);

  const saveSettings = () => {
    localStorage.setItem('gemini_api_key', apiKey);
    localStorage.setItem('venue_sources', JSON.stringify(sources));
    localStorage.setItem('manual_times_text', manualTimesText);
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
      const res = await axios.post(`${API_URL}/api/parse_image`, formData);
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

    // Build the dynamic constraints object using the user's provided URL or manual text
    const constraints = {
      fixed_schedule: fixedEvents,
      venues: {
        ice_rink: {
          scrape_url: sources[0]?.url || "",
          manual_times: manualTimesText,
          open_hours: {},
          reservation_required: true,
          reservation_advance_days: 1
        }
      }
    };

    try {
      const res = await axios.post(`${API_URL}/api/generate`, {
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

  const checkVenueTimes = async () => {
    setIsFetchingTimes(true);
    setError('');
    setVenueTimes(null);

    try {
      const res = await axios.post(`${API_URL}/api/check_venue_times`, {
        sources: sources,
        scrape_url: sources[0]?.url || "",
        manual_times: manualTimesText,
        gemini_api_key: apiKey, // It's optional on the backend now
        week_filter: weekFilter
      });
      setVenueTimes(res.data.times);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch venue times');
    } finally {
      setIsFetchingTimes(false);
    }
  };

  return (
    <div className="app-container">
      <header className="flex justify-between items-center mb-8">
        <h1>FloppaScheduler</h1>
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
        {/* TOOL 1: ICE RINK TRACKER */}
        <div className="glass-panel" style={{ border: '2px solid var(--primary)' }}>
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="flex items-center gap-2"><Sparkles color="var(--primary)" /> Tool 1: Ice Rink Tracker (Free)</h2>
              <p>Instantly fetch open hours from ActiveNet. No API Key required.</p>
            </div>
            <button
              className="secondary flex items-center gap-2"
              onClick={checkVenueTimes}
              disabled={isFetchingTimes}
            >
              🔍 {isFetchingTimes ? 'Fetching...' : 'Fetch Times'}
            </button>
          </div>

          <div className="flex-col gap-4">
            {sources.map((source, index) => (
              <div key={index} className="flex gap-2 items-center mb-2" style={{ background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '4px' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={source.url}
                    onChange={(e) => {
                      const newSources = [...sources];
                      newSources[index].url = e.target.value;
                      setSources(newSources);
                    }}
                    placeholder="Paste ActiveNet URL here..."
                  />
                  <input
                    type="text"
                    value={source.activity_filter}
                    onChange={(e) => {
                      const newSources = [...sources];
                      newSources[index].activity_filter = e.target.value;
                      setSources(newSources);
                    }}
                    placeholder="Activity Filter (e.g., Adult Skate)"
                  />
                </div>
                {sources.length > 1 && (
                  <button 
                    className="secondary" 
                    style={{ padding: '1rem', color: 'var(--error)' }}
                    onClick={() => {
                      const newSources = [...sources];
                      newSources.splice(index, 1);
                      setSources(newSources);
                    }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            
            <div className="flex justify-between items-center mt-2">
              <button 
                className="secondary"
                style={{ border: '1px dashed rgba(255,255,255,0.2)', background: 'transparent' }}
                onClick={() => setSources([...sources, { url: '', activity_filter: '' }])}
              >
                + Add Another City
              </button>
              
              <select
                style={{ width: '200px', padding: '0.8rem', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '4px' }}
                value={weekFilter}
                onChange={(e) => setWeekFilter(e.target.value)}
              >
                <option value="All Time">All Time</option>
                <option value="This Week">This Week</option>
                <option value="Next Week">Next Week</option>
              </select>
            </div>
          </div>

          {venueTimes && (
            <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                {Object.entries(venueTimes).map(([day, times]) => (
                  <div key={day} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: '8px' }}>
                    <h4 style={{ color: 'var(--primary)', marginBottom: '0.5rem' }}>{day}</h4>
                    {times.length > 0 ? (
                      <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                        {times.map((t, idx) => (
                          <li key={idx} style={{ marginBottom: '0.25rem', fontFamily: 'monospace' }}>{t}</li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.9rem' }}>Closed / No spots</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* TOOL 2: AI SCHEDULE GENERATOR */}
        <div className="glass-panel">
          <h2>Tool 2: AI Schedule Generator (Requires Gemini API Key)</h2>
          <p>Let AI merge your fixed classes, ice time, and personal goals into a perfect schedule.</p>
          
          <div className="mt-4">
            <h4 className="mb-2">A. Extract Fixed Schedule (Optional)</h4>

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

          <div className="mt-8">
            <h4 className="mb-2">B. Define Your Goals</h4>
            <p className="text-muted text-sm mb-2">The scheduler will automatically use the Ice Rink URL from Tool 1 if provided.</p>
            <textarea
              rows="4"
              placeholder="e.g. Schedule 3 ice training sessions (50 mins each) and 4 study sessions for Grind 75..."
              value={userIntent}
              onChange={(e) => setUserIntent(e.target.value)}
            ></textarea>
          </div>

          <button
            className="mt-6 flex items-center gap-2"
            style={{ width: '100%', justifyContent: 'center', padding: '1rem', fontSize: '1.2rem', background: 'var(--primary)' }}
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
              <label>Fallback Ice Rink Schedule (Manual Text)</label>
              <textarea
                rows="4"
                value={manualTimesText}
                onChange={(e) => setManualTimesText(e.target.value)}
                placeholder="Paste the copied schedule text here (e.g., 'Monday 11:00-11:50, Wednesday...')"
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
