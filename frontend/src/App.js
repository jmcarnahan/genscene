
import React, { useState, useEffect, useRef } from 'react';
import logo from './logo.svg';
import './App.css';
import Chatbot from './Chatbot';
import Sidebar from './Sidebar';
import axios from 'axios';

function App() {

  //const {user, setUser} = useState('user_id');
  const user = 'user_id';

  const [sidebarWidth, setSidebarWidth] = useState(300); // Initial sidebar width
  const [dragging, setDragging] = useState(false);
  const [thread, setThread] = useState(null);
  const [actor, setActor] = useState(null);
  const [threadList, setThreadList] = useState([]);
  const [actorList, setActorList] = useState([]);

  //need to get the user id from elsewhere


  const updateActor = async (actorName) => {
    await axios.get(
        `http://127.0.0.1:8000/api/actors/${actorName}`
    ).then(response => {
        console.log(`App: changed actor: ${response.data.actor_name}`);
        setActor(response.data); 
    }).catch(error => {
        console.error(error);
    });
  };  

  const updateThread = async (threadId) => {
    await axios.get(
        `http://127.0.0.1:8000/api/threads/${threadId}`
    ).then(response => {
        console.log(`App: changed thread: ${response.data.thread_id}`);
        setThread(response.data); 
    }).catch(error => {
        console.error(error);
    });
  };

  const updateThreadList = async () => {
    await axios.get(
        'http://127.0.0.1:8000/api/threads/',
        { params: { user: user } }
    ).then(response => {
        console.log(`App: updated thread list: ${response.data}`);
        setThreadList(response.data); 
    }).catch(error => {
        console.error(error);
    });
  };

  const updateActorList = async () => {
    await axios.get(
        'http://127.0.0.1:8000/api/actors/'
    ).then(response => {
        console.log(`App: updated actor list: ${response.data}`);
        setActorList(response.data); 
    }).catch(error => {
        console.error(error);
    });
  };

  // set the thread and actor to the home page by default
  useEffect(() => {
    updateActor('home');
    // updateThread(null);
    updateThreadList();
    updateActorList();
  }, []);  

  const handleActorChange = (actorName) => {
    updateActor(actorName);
  }

  const handleThreadChange = (threadId) => {
    updateThread(threadId);
  }

  const handleThreadListChange = () => {
    updateThreadList();
  }

  // Define minimum and maximum sidebar widths
  const minSidebarWidth = 300; 
  const maxSidebarWidth = 500; 

  const startDragging = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const stopDragging = () => {
    if (dragging) {
      setDragging(false);
    }
  };

  const onDrag = (e) => {
    if (dragging) {
      const newWidth = e.clientX;
      // Clamp newWidth between minWidth and maxWidth
      const clampedWidth = Math.min(Math.max(newWidth, minSidebarWidth), maxSidebarWidth);
      setSidebarWidth(clampedWidth);
    }
  };

  return (
    <div className="app-container" onMouseMove={onDrag} onMouseUp={stopDragging} onMouseLeave={stopDragging}>
      <div className="sidebar-container" style={{ width: sidebarWidth }}>
        <Sidebar 
          user={user}
          actor={actor}
          thread={thread}
          threadList={threadList}
          onThreadChange={handleThreadChange}
          onThreadListChange={handleThreadListChange}
        />
      </div>
      <div className="resizer" onMouseDown={startDragging}></div>
      <div className="content-container">
        <Chatbot 
          user={user} 
          actor={actor}
          thread={thread} 
          actorList={actorList}
          onActorChange={handleActorChange}
          onThreadListChange={handleThreadListChange}
        />
      </div>
    </div>
  );

}

export default App;