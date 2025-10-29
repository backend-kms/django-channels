import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [roomName, setRoomName] = useState('');
  const [currentRoom, setCurrentRoom] = useState('');
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [socket, setSocket] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [stats, setStats] = useState(null);
  const [connected, setConnected] = useState(false);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [newRoomData, setNewRoomData] = useState({
    name: '',
    description: '',
    max_members: 100
  });

  // 초기 데이터 로드
  useEffect(() => {
    fetchRooms();
    fetchStats();
  }, []);

  // 방 목록 가져오기
  const fetchRooms = () => {
    axios.get('http://localhost:8000/chat/api/rooms/')
      .then(res => {
        console.log('방 목록:', res.data);
        if (res.data.success) {
          setRooms(res.data.rooms);
        }
      })
      .catch(err => console.log('에러:', err));
  };

  // 통계 가져오기
  const fetchStats = () => {
    axios.get('http://localhost:8000/chat/api/stats/')
      .then(res => {
        console.log('통계:', res.data);
        if (res.data.success) {
          setStats(res.data.stats);
        }
      })
      .catch(err => console.log('통계 에러:', err));
  };

  // 방 생성
  const createRoom = () => {
    if (!newRoomData.name.trim()) return;

    axios.post('http://localhost:8000/chat/api/rooms/create/', newRoomData)
      .then(res => {
        console.log('방 생성:', res.data);
        if (res.data.success) {
          alert('방이 생성되었습니다!');
          setShowCreateRoom(false);
          setNewRoomData({ name: '', description: '', max_members: 100 });
          fetchRooms(); // 방 목록 새로고침
        }
      })
      .catch(err => {
        console.log('방 생성 실패:', err);
        if (err.response?.data?.error) {
          alert(err.response.data.error);
        }
      });
  };

  // 방 입장
  const joinRoom = () => {
    if (!roomName) return;

    axios.get(`http://localhost:8000/chat/api/room/${roomName}/`)
      .then(res => {
        console.log('방 정보:', res.data);
        if (res.data.success) {
          setCurrentRoom(roomName);
          
          const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomName}/`);
          
          ws.onopen = () => {
            console.log('WebSocket 연결됨');
            setSocket(ws);
            setConnected(true);
          };
          
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('메시지 받음:', data);
            setMessages(prev => [...prev, {
              id: Date.now(),
              text: data.message,
              author: data.author || 'Anonymous',
              time: new Date().toLocaleTimeString()
            }]);
          };
          
          ws.onclose = () => {
            console.log('WebSocket 연결 끊김');
            setSocket(null);
            setConnected(false);
          };
        }
      })
      .catch(err => console.log('방 입장 실패:', err));
  };

  // 메시지 보내기
  const sendMessage = () => {
    if (socket && message.trim()) {
      socket.send(JSON.stringify({ message: message.trim() }));
      setMessage('');
    }
  };

  // 방 나가기
  const leaveRoom = () => {
    if (socket) socket.close();
    setCurrentRoom('');
    setMessages([]);
    setConnected(false);
  };

  // Enter 키로 전송
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      if (currentRoom) {
        sendMessage();
      } else {
        joinRoom();
      }
    }
  };

  return (
    <div className="app">
      {!currentRoom ? (
        // 🏠 방 선택 화면
        <div className="home">
          <div className="hero">
            <h1>💬</h1>
            <h2>Simple Chat</h2>
            <p>간단하고 빠른 실시간 채팅</p>
          </div>

          {/* 통계 정보 */}
          {stats && (
            <div className="stats-card">
              <h4>📊 서버 현황</h4>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-number">{stats.total_rooms}</span>
                  <span className="stat-label">총 방</span>
                </div>
                <div className="stat-item">
                  <span className="stat-number">{stats.online_users}</span>
                  <span className="stat-label">온라인</span>
                </div>
                <div className="stat-item">
                  <span className="stat-number">{stats.today_messages}</span>
                  <span className="stat-label">오늘 메시지</span>
                </div>
              </div>
            </div>
          )}

          <div className="join-card">
            <h3>방 입장하기</h3>
            <div className="input-group">
              <input
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="방 이름을 입력하세요"
                className="room-input"
              />
              <button onClick={joinRoom} className="join-btn">
                입장 →
              </button>
            </div>
          </div>

          {/* 방 생성 모달 */}
          {showCreateRoom && (
            <div className="create-room-modal">
              <div className="modal-content">
                <h3>새 채팅방 만들기</h3>
                <input
                  value={newRoomData.name}
                  onChange={(e) => setNewRoomData({...newRoomData, name: e.target.value})}
                  placeholder="방 이름"
                  className="modal-input"
                />
                <input
                  value={newRoomData.description}
                  onChange={(e) => setNewRoomData({...newRoomData, description: e.target.value})}
                  placeholder="방 설명 (선택사항)"
                  className="modal-input"
                />
                <div className="modal-buttons">
                  <button onClick={createRoom} className="create-btn">생성</button>
                  <button onClick={() => setShowCreateRoom(false)} className="cancel-btn">취소</button>
                </div>
              </div>
            </div>
          )}

          {rooms.length > 0 && (
            <div className="rooms-section">
              <div className="rooms-header">
                <h4>💭 기존 채팅방 ({rooms.length}개)</h4>
                <button onClick={() => setShowCreateRoom(true)} className="create-room-btn">
                  ➕ 새 방
                </button>
              </div>
              <div className="rooms-grid">
                {rooms.map(room => (
                  <div 
                    key={room.id} 
                    className="room-card"
                    onClick={() => setRoomName(room.name)}
                  >
                    <div className="room-title">{room.name}</div>
                    <div className="room-desc">{room.description}</div>
                    <div className="room-meta">
                      👥 {room.member_count}/{room.max_members}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        // 💬 채팅 화면
        <div className="chat">
          <div className="chat-header">
            <div className="room-title">
              <span className="room-icon">💬</span>
              <span>{currentRoom}</span>
            </div>
            <div className="header-actions">
              <span className={`status ${connected ? 'online' : 'offline'}`}>
                {connected ? '🟢 온라인' : '🔴 오프라인'}
              </span>
              <button onClick={leaveRoom} className="leave-btn">
                나가기
              </button>
            </div>
          </div>

          <div className="messages">
            {messages.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">🌟</span>
                <p>첫 번째 메시지를 보내보세요!</p>
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className="message">
                  <div className="message-info">
                    <span className="author">{msg.author}</span>
                    <span className="time">{msg.time}</span>
                  </div>
                  <div className="message-text">{msg.text}</div>
                </div>
              ))
            )}
          </div>

          <div className="message-input">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="메시지를 입력하세요..."
              disabled={!connected}
            />
            <button 
              onClick={sendMessage} 
              disabled={!connected || !message.trim()}
              className="send-btn"
            >
              전송
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;