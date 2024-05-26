import React, { useState, useEffect, useRef } from 'react';
import { Container, Form, Row, Col, Button, ListGroup } from 'react-bootstrap';
// import 'bootstrap/dist/css/bootstrap.min.css';
import axios from 'axios';
import './Sidebar.css';



function Sidebar ({user, actor, thread, threadList, onThreadChange, onThreadListChange}) {
    const [threadId, setThreadId] = useState(null);

    useEffect(() => {
        if (threadId !== null) {
            //console.log('Sidebar: changed thread:', threadId);
            onThreadChange(threadId);
        }
    }, [threadId]);

    const handleThreadClick = (newThreadId) => {
        if (threadId !== newThreadId) {
            setThreadId(newThreadId);
        }
    };

    const handleNewThread = async () => {
        await axios.post(
            'http://127.0.0.1:8000/api/threads/',
            { user: user }
        ).then(response => {
            //console.log('Sidebar: created new thread: ', response.data);
            onThreadListChange(); 
        }).catch(error => {
            console.error(error);
        });
    }

    return (
        <div>

            <Container className="sidebar-thread-container">
                <div className="header-text">
                    <span>Threads</span>{' '}
                    <button onClick={handleNewThread} className="new-thread-button" aria-label="Add">+</button>
                </div>
                <ListGroup >
                    {threadList.map((threadItem, index) => (
                        <ListGroup.Item
                            className="sidebar-thread"
                            action
                            active={threadItem.thread_id === threadId}
                            key={threadItem.thread_id}
                            onClick={() => handleThreadClick(threadItem.thread_id)}
                        >
                            {threadItem.name}
                        </ListGroup.Item>
                    ))}
                </ListGroup>
            </Container>
                        
        </div>

    );

}

export default Sidebar;