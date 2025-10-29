import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

// 🔧 API 설정
const API_BASE_URL = 'http://localhost:8000/chat';
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = false;

function App() {
  // 🔑 인증 상태
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // 🏠 방 관련 상태
  const [rooms, setRooms] = useState([]);
  const [stats, setStats] = useState({});
  const [currentRoom, setCurrentRoom] = useState('');
  const [roomName, setRoomName] = useState('');
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  
  // 💬 채팅 상태
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [connected, setConnected] = useState(false);
  
  // 📝 폼 상태
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [roomForm, setRoomForm] = useState({ name: '', description: '', max_members: 100 });

  // 🔑 JWT 토큰 관리
  const setAuthToken = useCallback((token) => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('access_token', token);
      console.log('🔑 토큰 설정됨');
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      console.log('🚫 토큰 제거됨');
    }
  }, []);

  // 📊 데이터 로드 함수들
  const fetchRooms = useCallback(async () => {
    try {
      const response = await axios.get('/api/rooms/');
      if (response.data.results) {
        setRooms(response.data.results);
        console.log(`🏠 ${response.data.results.length}개 방 로드됨`);
      }
    } catch (error) {
      console.error('❌ 방 목록 로드 실패:', error);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get('/api/stats/');
      if (response.data.success) {
        setStats(response.data.stats);
        console.log('📊 통계 로드됨');
      }
    } catch (error) {
      console.error('❌ 통계 로드 실패:', error);
    }
  }, []);

  // 🔐 로그인
  const handleLogin = async () => {
    try {
      if (!loginForm.username.trim() || !loginForm.password.trim()) {
        alert('아이디와 비밀번호를 입력해주세요.');
        return;
      }

      console.log('🔐 로그인 시도...');
      const response = await axios.post('/api/auth/login/', loginForm);
      
      if (response.data.success) {
        const { access_token, refresh_token, user, message } = response.data;
        
        // 토큰과 사용자 정보 저장
        setAuthToken(access_token);
        localStorage.setItem('refresh_token', refresh_token);
        localStorage.setItem('user', JSON.stringify(user));
        
        setUser(user);
        setIsAuthenticated(true);
        setLoginForm({ username: '', password: '' });
        
        alert(message);
        console.log('✅ 로그인 성공:', user.username);
        
        // 데이터 새로고침
        fetchRooms();
        fetchStats();
      }
    } catch (error) {
      console.error('❌ 로그인 실패:', error);
      const errorMessage = error.response?.data?.error || '로그인에 실패했습니다.';
      alert(errorMessage);
    }
  };

  // 🚪 로그아웃
  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await axios.post('/api/auth/logout/', { refresh_token: refreshToken });
      }
    } catch (error) {
      console.error('❌ 로그아웃 API 오류:', error);
    } finally {
      // WebSocket 연결 해제
      if (socket) {
        socket.close();
      }
      
      // 상태 초기화
      setAuthToken(null);
      setUser(null);
      setIsAuthenticated(false);
      setCurrentRoom('');
      setMessages([]);
      setConnected(false);
      setSocket(null);
      
      console.log('👋 로그아웃 완료');
      
      // 데이터 새로고침
      fetchRooms();
      fetchStats();
    }
  };

  // 🏠 방 생성
  const handleCreateRoom = async () => {
    try {
      if (!isAuthenticated) {
        alert('로그인이 필요합니다.');
        return;
      }

      if (!roomForm.name.trim()) {
        alert('방 이름을 입력해주세요.');
        return;
      }

      console.log('🏠 방 생성 시도:', roomForm.name);
      const response = await axios.post('/api/rooms/create/', roomForm);
      
      if (response.data.success) {
        alert(response.data.message);
        setShowCreateRoom(false);
        setRoomForm({ name: '', description: '', max_members: 100 });
        fetchRooms();
        console.log('✅ 방 생성 성공');
      }
    } catch (error) {
      console.error('❌ 방 생성 실패:', error);
      const errorMessage = error.response?.data?.error || '방 생성에 실패했습니다.';
      alert(errorMessage);
    }
  };

  // 🗑️ 방 삭제
  const handleDeleteRoom = async (roomId, roomName) => {
    try {
      if (!window.confirm(`정말로 '${roomName}' 방을 삭제하시겠습니까?`)) {
        return;
      }

      console.log('🗑️ 방 삭제 시도:', roomName);
      const response = await axios.delete(`/api/rooms/delete/${roomId}/`);
      
      if (response.data.success) {
        alert(response.data.message);
        
        // 현재 방이 삭제된 방이면 나가기
        if (currentRoom === roomName) {
          handleLeaveRoom();
        }
        
        fetchRooms();
        console.log('✅ 방 삭제 성공');
      }
    } catch (error) {
      console.error('❌ 방 삭제 실패:', error);
      const errorMessage = error.response?.data?.error || '방 삭제에 실패했습니다.';
      alert(errorMessage);
    }
  };

  // 🚪 방 입장
  const handleJoinRoom = async (targetRoomName) => {
    try {
      if (!isAuthenticated) {
        alert('로그인이 필요합니다.');
        return;
      }

      console.log('🚪 방 입장 시도:', targetRoomName);
      const response = await axios.get(`/api/room/${targetRoomName}/`);
      
      if (response.data.success) {
        setCurrentRoom(targetRoomName);
        setMessages([]);
        
        // WebSocket 연결
        const ws = new WebSocket(`ws://localhost:8000/ws/chat/${targetRoomName}/`);
        
        ws.onopen = () => {
          console.log('🔗 WebSocket 연결됨');
          setSocket(ws);
          setConnected(true);
        };
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          console.log('📨 메시지 수신:', data);
          
          setMessages(prev => [...prev, {
            id: Date.now() + Math.random(),
            text: data.message,
            author: data.username || data.author || 'Anonymous',
            time: new Date().toLocaleTimeString(),
            isSystem: data.type === 'system'
          }]);
        };
        
        ws.onclose = () => {
          console.log('❌ WebSocket 연결 해제됨');
          setSocket(null);
          setConnected(false);
        };
        
        ws.onerror = (error) => {
          console.error('❌ WebSocket 오류:', error);
        };
        
        console.log('✅ 방 입장 성공:', targetRoomName);
      }
    } catch (error) {
      console.error('❌ 방 입장 실패:', error);
      if (error.response?.status === 404) {
        alert('존재하지 않는 채팅방입니다.');
      } else {
        alert('방 입장에 실패했습니다.');
      }
    }
  };

  // 📤 메시지 전송
  const handleSendMessage = () => {
    if (socket && message.trim() && connected) {
      socket.send(JSON.stringify({
        type: 'chat_message',
        message: message.trim(),
        username: user?.username
      }));
      setMessage('');
      console.log('📤 메시지 전송됨');
    } else if (!connected) {
      alert('채팅방에 연결되지 않았습니다.');
    }
  };

  // 🚪 방 나가기
  const handleLeaveRoom = () => {
    if (socket) {
      socket.close();
    }
    setCurrentRoom('');
    setMessages([]);
    setConnected(false);
    setSocket(null);
    console.log('🚪 방에서 나감');
  };

  // ⌨️ 키보드 이벤트
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      if (!isAuthenticated) {
        handleLogin();
      } else if (currentRoom) {
        handleSendMessage();
      } else if (roomName) {
        handleJoinRoom(roomName);
      }
    }
  };

  // 🔄 초기화
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');
        
        if (token && savedUser) {
          setAuthToken(token);
          setUser(JSON.parse(savedUser));
          setIsAuthenticated(true);
          console.log('💾 로그인 상태 복원됨');
          
          // 토큰 유효성 검사
          try {
            await axios.get('/api/auth/profile/');
            console.log('✅ 토큰 유효함');
          } catch (error) {
            console.log('❌ 토큰 만료됨');
            setAuthToken(null);
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      } catch (error) {
        console.error('❌ 인증 초기화 실패:', error);
        setAuthToken(null);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
        fetchRooms();
        fetchStats();
      }
    };

    initializeAuth();
  }, [setAuthToken, fetchRooms, fetchStats]);

  // 🔄 정기 데이터 새로고침
  useEffect(() => {
    const interval = setInterval(() => {
      fetchRooms();
      fetchStats();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchRooms, fetchStats]);

  // 🧹 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [socket]);

  // 🔄 로딩 화면
  if (isLoading) {
    return (
      <div className="app">
        <div className="loading-container">
          <div className="spinner"></div>
          <h2>로딩 중...</h2>
          <p>잠시만 기다려주세요</p>
        </div>
      </div>
    );
  }

  // 💬 채팅 화면
  if (currentRoom) {
    return (
      <div className="app chat-app">
        <div className="chat-header">
          <div className="room-info">
            <h1>💬 {currentRoom}</h1>
            <span className={`status ${connected ? 'online' : 'offline'}`}>
              {connected ? '🟢 연결됨' : '🔴 연결 안됨'}
            </span>
          </div>
          <div className="header-actions">
            <span className="user-name">👋 {user?.username}</span>
            <button onClick={handleLeaveRoom} className="btn btn-secondary">
              방 나가기
            </button>
            <button onClick={handleLogout} className="btn btn-outline">
              로그아웃
            </button>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">🌟</span>
              <p>첫 번째 메시지를 보내보세요!</p>
            </div>
          ) : messages.map(msg => (
            <div 
              key={msg.id} 
              className={`message ${
                msg.isSystem ? 'system-message' : 
                msg.author === user?.username ? 'my-message' : 'other-message'
              }`}
            >
              <div className="message-header">
                <span className="author">{msg.author}</span>
                <span className="time">{msg.time}</span>
              </div>
              <div className="message-bubble">
                <div className="message-content">{msg.text}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="message-input">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="메시지를 입력하세요..."
            disabled={!connected}
            className="message-field"
          />
          <button 
            onClick={handleSendMessage} 
            disabled={!connected || !message.trim()}
            className="btn btn-primary"
          >
            전송
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      {/* 헤더 */}
      <header className="app-header">
        <h1>🚀 Simple Chat</h1>
        <div className="header-actions">
          {isAuthenticated ? (
            <div className="user-menu">
              <span className="user-info">👋 {user.username}님</span>
              <button className="btn btn-secondary" onClick={handleLogout}>
                로그아웃
              </button>
            </div>
          ) : (
            <div className="login-section">
              <input
                type="text"
                value={loginForm.username}
                onChange={(e) => setLoginForm({...loginForm, username: e.target.value})}
                onKeyPress={handleKeyPress}
                placeholder="아이디"
                className="login-input"
              />
              <input
                type="password"
                value={loginForm.password}
                onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                onKeyPress={handleKeyPress}
                placeholder="비밀번호"
                className="login-input"
              />
              <button className="btn btn-primary" onClick={handleLogin}>
                로그인
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main className="main-content">
        {/* 통계 섹션 */}
        <section className="stats-section">
          <h2>📊 서버 통계</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">{stats.total_rooms || 0}</div>
              <div className="stat-label">활성 채팅방</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{stats.total_users || 0}</div>
              <div className="stat-label">총 사용자</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{stats.online_users || 0}</div>
              <div className="stat-label">온라인 사용자</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{stats.today_messages || 0}</div>
              <div className="stat-label">오늘 메시지</div>
            </div>
          </div>
        </section>

        {/* 방 입장 섹션 */}
        <section className="join-section">
          <h2>🚪 채팅방 입장</h2>
          <div className="join-form">
            <input
              type="text"
              value={roomName}
              onChange={(e) => setRoomName(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="방 이름을 입력하세요"
              className="room-input"
            />
            <button 
              onClick={() => handleJoinRoom(roomName)} 
              disabled={!isAuthenticated || !roomName.trim()}
              className="btn btn-primary"
            >
              입장하기
            </button>
          </div>
        </section>

        {/* 방 생성 섹션 */}
        {isAuthenticated && (
          <section className="create-section">
            <h2>🏠 새 채팅방 만들기</h2>
            {!showCreateRoom ? (
              <button onClick={() => setShowCreateRoom(true)} className="btn btn-success">
                방 만들기
              </button>
            ) : (
              <div className="create-form">
                <input
                  type="text"
                  placeholder="방 이름"
                  value={roomForm.name}
                  onChange={(e) => setRoomForm({...roomForm, name: e.target.value})}
                  className="form-input"
                />
                <input
                  type="text"
                  placeholder="방 설명 (선택사항)"
                  value={roomForm.description}
                  onChange={(e) => setRoomForm({...roomForm, description: e.target.value})}
                  className="form-input"
                />
                <input
                  type="number"
                  placeholder="최대 인원"
                  value={roomForm.max_members}
                  onChange={(e) => setRoomForm({...roomForm, max_members: e.target.value})}
                  className="form-input"
                  min="1"
                  max="1000"
                />
                <div className="form-actions">
                  <button onClick={handleCreateRoom} className="btn btn-success">
                    생성
                  </button>
                  <button onClick={() => setShowCreateRoom(false)} className="btn btn-secondary">
                    취소
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {/* 채팅방 목록 */}
        <section className="rooms-section">
          <h2>💭 채팅방 목록</h2>
          {rooms.length === 0 ? (
            <div className="empty-rooms">
              <p>아직 채팅방이 없습니다.</p>
              {!isAuthenticated && <p>로그인하면 채팅방을 만들 수 있어요!</p>}
            </div>
          ) : (
            <div className="rooms-grid">
              {rooms.map(room => (
                <div key={room.id} className="room-card">
                  <div className="room-header">
                    <h3 className="room-name">{room.name}</h3>
                    {room.can_delete && isAuthenticated && (
                      <button
                        onClick={() => handleDeleteRoom(room.id, room.name)}
                        className="delete-btn"
                        title="방 삭제"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                  <p className="room-description">{room.description}</p>
                  <div className="room-info">
                    <span className="room-members">
                      👥 {room.member_count}/{room.max_members}
                    </span>
                    <span className="room-creator">👤 {room.created_by}</span>
                  </div>
                  <div className="room-footer">
                    <span className="room-date">
                      📅 {new Date(room.created_at).toLocaleDateString()}
                    </span>
                    <button 
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        setRoomName(room.name);
                        handleJoinRoom(room.name);
                      }}
                      disabled={!isAuthenticated}
                    >
                      입장하기
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;