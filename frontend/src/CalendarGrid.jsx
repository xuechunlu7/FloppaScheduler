import React from 'react';
import './Calendar.css';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const START_HOUR = 8;
const END_HOUR = 23;
const TOTAL_HOURS = END_HOUR - START_HOUR;

const parseTime = (timeStr) => {
  const [hours, mins] = timeStr.split(':').map(Number);
  return hours + mins / 60;
};

const CalendarGrid = ({ events = [] }) => {
  // Generate time labels (e.g., "08:00", "09:00")
  const timeLabels = [];
  for (let i = START_HOUR; i < END_HOUR; i++) {
    timeLabels.push(`${i.toString().padStart(2, '0')}:00`);
  }

  // Group events by day
  const eventsByDay = {};
  DAYS.forEach(day => eventsByDay[day] = []);
  
  if (Array.isArray(events)) {
    events.forEach(event => {
      if (eventsByDay[event.day_of_week]) {
        eventsByDay[event.day_of_week].push(event);
      }
    });
  }

  return (
    <div className="calendar-container">
      <div className="calendar-header">
        <div className="calendar-header-cell">Time</div>
        {DAYS.map(day => (
          <div key={day} className="calendar-header-cell">{day.substring(0, 3)}</div>
        ))}
      </div>
      
      <div className="calendar-body">
        {/* Time Column */}
        <div className="time-column" style={{ gridRow: `1 / span ${TOTAL_HOURS * 2}` }}>
          {timeLabels.map(time => (
            <div key={time} className="time-slot">{time}</div>
          ))}
        </div>

        {/* Day Columns */}
        {DAYS.map((day, dayIdx) => (
          <div key={day} className="day-column" style={{ gridColumn: dayIdx + 2, gridRow: `1 / span ${TOTAL_HOURS * 2}` }}>
            {eventsByDay[day].map((event, idx) => {
              const startT = parseTime(event.start_time);
              const endT = parseTime(event.end_time);
              
              // Only render if it falls within our view
              if (startT >= END_HOUR || endT <= START_HOUR) return null;
              
              const boundedStart = Math.max(startT, START_HOUR);
              const boundedEnd = Math.min(endT, END_HOUR);
              
              const topPercent = ((boundedStart - START_HOUR) / TOTAL_HOURS) * 100;
              const heightPercent = ((boundedEnd - boundedStart) / TOTAL_HOURS) * 100;

              let typeClass = 'event-fixed';
              if (event.event_type === 'additional') typeClass = 'event-additional';
              if (event.event_type === 'recovery') typeClass = 'event-recovery';

              return (
                <div 
                  key={idx} 
                  className={`event-card ${typeClass}`}
                  style={{ top: `${topPercent}%`, height: `${heightPercent}%` }}
                >
                  <div className="event-title">{event.title}</div>
                  <div className="event-time">{event.start_time} - {event.end_time}</div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default CalendarGrid;
