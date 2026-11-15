# 📅 Daily Planner - AI-Powered Smart Productivity Assistant

A powerful desktop daily planner with AI guidance, smart reminders, and comprehensive task management to supercharge your productivity.

## ✨ Features

### 🤖 AI-Powered Intelligence
- **Smart Task Guidance**: Get AI-generated step-by-step breakdowns for any task
- **Auto-Prioritization**: AI analyzes tasks and suggests optimal priority levels
- **Intelligent Insights**: Context-aware recommendations based on deadlines and complexity
- **Task Coaching**: Personalized tips and time estimates

### 🔔 Smart Reminder System
- **24-Hour Alert**: Day-before notification
- **12-Hour Alert**: Half-day warning
- **2-Hour Alert**: Final reminder before deadline
- **Overdue Alerts**: Never forget past-due tasks
- **Desktop Notifications**: Non-intrusive system notifications

### 🌅 Morning Check-in (8:00 AM)
- Automatically pops up at 8:00 AM daily
- Clean, distraction-free interface to plan your day
- Quick task entry with keyboard shortcuts

### 📝 Advanced Task Management
- **Text Input**: Type tasks quickly with Enter to add
- **Voice Input**: Framework ready (coming soon)
- **Priority Levels**: High (Red), Medium (Yellow), Low (Green)
- **Deadlines**: Optional deadline tracking with countdown
- **Smart Sorting**: Automatically sorts by priority and completion status
- **Quick Actions**: Add from clipboard, clear completed tasks instantly

### ⚡ Real-Time Features
- **Add Anytime**: Add tasks whenever inspiration strikes, not just at 8 AM
- **Remove Anytime**: Delete or modify tasks with one click
- **Instant Sync**: All changes saved immediately
- **Live Updates**: Task list updates in real-time

### 📊 Performance Analytics
- Daily completion rate
- Weekly overview with trends
- Task distribution by priority
- Visual progress indicators
- Pattern recognition over time

## 🚀 Installation

### Requirements
```bash
pip install schedule plyer requests --break-system-packages
```

Or use the automated installer:
```bash
chmod +x install.sh
./install.sh
```

**Dependencies:**
- Python 3.x with tkinter (usually pre-installed)
- schedule (for 8 AM automation)
- plyer (for desktop notifications)
- requests (for AI features)

### Quick Start

1. **Run the planner immediately**:
```bash
python3 daily_planner.py
```

2. **Set up automatic 8 AM launch**:
```bash
python3 scheduler.py
```

Keep the scheduler running in the background (see setup instructions below).

## 🤖 AI Setup (Optional but Recommended)

### Get Your Anthropic API Key

1. Visit https://console.anthropic.com/
2. Sign up and create an API key
3. Set environment variable:

```bash
# Linux/Mac
export ANTHROPIC_API_KEY="your-api-key-here"

# Windows
set ANTHROPIC_API_KEY=your-api-key-here
```

### Cost
- Pay-as-you-go pricing
- ~$0.01-0.03 per task guidance
- ~$1-5 monthly for typical use
- Optional - app works great without AI

**See AI_FEATURES.md for complete AI setup guide**

## 🔧 Setup for Auto-Launch at 8 AM

### On Linux/Ubuntu:
1. **Using systemd (recommended)**:
   
Create a service file:
```bash
sudo nano /etc/systemd/system/daily-planner.service
```

Add this content:
```ini
[Unit]
Description=Daily Planner Scheduler
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/planner/directory
ExecStart=/usr/bin/python3 /path/to/planner/directory/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable daily-planner.service
sudo systemctl start daily-planner.service
```

2. **Using crontab**:
```bash
crontab -e
```
Add:
```
@reboot cd /path/to/planner && nohup python3 scheduler.py &
```

### On macOS:
Create a LaunchAgent plist file at `~/Library/LaunchAgents/com.dailyplanner.scheduler.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyplanner.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/scheduler.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.dailyplanner.scheduler.plist
```

### On Windows:
Use Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: "When I log on"
4. Action: Start program `python.exe scheduler.py`

## 💡 Usage Tips

### 🤖 AI Features

**Getting Task Guidance:**
1. Click 🤖 button next to any task
2. Wait 2-3 seconds for AI analysis
3. Read personalized breakdown and tips

**Auto-Prioritizing:**
1. Type your task
2. Click "🤖 AI Prioritize"
3. AI suggests priority level
4. Adjust if needed and add

**Quick Actions:**
- 📋 Add from Clipboard: Paste tasks instantly
- 🗑️ Clear Completed: Remove all done tasks

### 🔔 Smart Reminders

Automatic notifications at:
- ⏰ 24 hours before deadline
- ⏰ 12 hours before deadline  
- ⏰ 2 hours before deadline
- 🚨 Overdue alert if missed

No configuration needed - works automatically!

### ⚡ Anytime Task Management

**Add Tasks Anytime:**
- Not limited to 8 AM
- Open planner whenever needed
- Click anywhere to add new tasks
- Quick entry with Enter key

**Remove Tasks Anytime:**
- Click 🗑️ to delete
- Use "Clear Completed" for bulk removal
- Changes save instantly

### Keyboard Shortcuts
- **Enter**: Add task after typing
- Tasks are auto-saved immediately

### Priority Guidelines
- **High** (🔴): Urgent deadlines, critical tasks
- **Medium** (🟡): Important but flexible timing
- **Low** (🟢): Nice to do, low urgency

### Deadline Format
- Use format: `YYYY-MM-DD` (e.g., 2024-12-25)
- Leave blank if no deadline

### Best Practices
1. **Morning**: Add all tasks at 8 AM with priorities
2. **Throughout Day**: Check off tasks as you complete them
3. **Evening**: Review stats to see your performance
4. **Weekly**: Use weekly view to track patterns

## 📊 Understanding Your Stats

### Daily Performance
- **Completion Rate**: % of tasks completed today
- **Priority Distribution**: How you allocate effort

### Weekly Overview
- Shows 7-day trend
- Helps identify productive days
- Track improvement over time

## 🗂️ Data Storage

All data is stored in: `~/planner_data.json`

- Automatic backup on every save
- JSON format for easy export/backup
- Tasks organized by date

## 🔮 Recent Updates

### ✅ Just Added!
- 🤖 **AI Task Guidance**: Get intelligent breakdowns for any task
- 🎯 **Smart Auto-Prioritization**: AI suggests optimal priorities
- 🔔 **Multi-Stage Reminders**: 24h, 12h, 2h, and overdue alerts
- 📋 **Quick Actions**: Clipboard paste and bulk clear
- ⚡ **Anytime Access**: Add/remove tasks whenever you need
- 💬 **AI Assistant Panel**: Dedicated help interface
- 🔄 **Real-time Notifications**: Desktop alerts for deadlines

## 🔮 Coming Soon

- 🎤 **Voice Input**: Speak your tasks instead of typing
- 📱 **Mobile Sync**: Access on phone
- 📈 **Advanced Analytics**: Deep productivity insights with AI
- 🤖 **Smart Suggestions**: Proactive task recommendations
- 📅 **Calendar Integration**: Sync with Google/Outlook
- 🌙 **Evening Review**: End-of-day AI summary
- 🔗 **Team Features**: Collaborate on shared tasks

## 🛠️ Troubleshooting

**Planner doesn't appear at 8 AM**:
- Check if scheduler.py is running
- Verify system time is correct
- Check service/cron logs

**Tasks not saving**:
- Ensure write permissions for home directory
- Check `~/planner_data.json` exists

**GUI issues**:
- Ensure tkinter is installed: `python3 -m tkinter`

## 📝 Manual Test

To test without waiting for 8 AM:
```python
# Edit scheduler.py and uncomment this line:
launch_planner()
```

## 🤝 Tips for Maximum Productivity

1. **Start Small**: Begin with 3-5 tasks per day
2. **Be Specific**: "Email John about project" vs "Email stuff"
3. **Use Priorities**: Not everything is high priority
4. **Review Daily**: Check stats to understand your patterns
5. **Adjust**: If always incomplete, you're overplanning

## 📄 License

Free to use and modify for personal productivity!

---

**Made with ❤️ for productivity enthusiasts**

Need help? Found a bug? Want a feature? Feel free to modify the code!
