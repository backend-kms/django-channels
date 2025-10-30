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
  const [myRooms, setMyRooms] = useState([]);
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

  const fetchMyRooms = useCallback(async () => {
    if (!isAuthenticated) {
      setMyRooms([]);
      return;
    }
    
    try {
      const response = await axios.get('/api/my-rooms/');
      setMyRooms(response.data || []);
      console.log(`🏠 내 방 ${response.data?.length || 0}개 로드됨`);
    } catch (error) {
      console.error('❌ 내 방 목록 로드 실패:', error);
      setMyRooms([]);
    }
  }, [isAuthenticated]);

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
        fetchMyRooms();
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
      setMyRooms([]);
      
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
        fetchMyRooms();
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
        fetchMyRooms();
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

      // 1. 방 입장 API 호출
      const joinResponse = await axios.post(`/api/rooms/${targetRoomName}/join/`);
      
      if (joinResponse.data.success) {
        console.log('✅ 서버 입장 성공:', joinResponse.data.message);
        
        // 2. 채팅 메시지 히스토리 로드
        const messagesResponse = await axios.get(`/api/rooms/${targetRoomName}/messages/`);
        if (messagesResponse.data) {
          const loadedMessages = messagesResponse.data.map(msg => ({
            id: msg.id,
            text: msg.content || msg.message,
            author: msg.username || 'Anonymous',
            time: new Date(msg.created_at).toLocaleTimeString(),
            isSystem: msg.message_type === 'system'
          }));
          setMessages(loadedMessages);
        }

        // 3. 방 상태 설정
        setCurrentRoom(targetRoomName);
        
        // 4. WebSocket 연결
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

        // 5. 내 방 목록 새로고침
        fetchMyRooms();
        
        console.log('✅ 방 입장 완료:', targetRoomName);
      }
    } catch (error) {
      console.error('❌ 방 입장 실패:', error);
      if (error.response?.status === 404) {
        alert('존재하지 않는 채팅방입니다.');
      } else if (error.response?.status === 400) {
        const errorMessage = error.response?.data?.error || '방이 가득 찼습니다.';
        alert(errorMessage);
      } else {
        const errorMessage = error.response?.data?.error || error.response?.data?.detail || '방 입장에 실패했습니다.';
        alert(errorMessage);
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

  // 🚪 방 나가기 (서버에 퇴장 알림 + 완전 정리)
  const handleLeaveRoom = async () => {
    if (!currentRoom) return;

    // 진짜 나갈 건지 확인
    if (!window.confirm(`'${currentRoom}' 방에서 나가시겠습니까?\n\n나가면 서버에서도 완전히 퇴장 처리됩니다.`)) {
      return;
    }

    try {
      // 서버에 퇴장 알림
      await axios.post(`/api/rooms/${currentRoom}/leave/`);
      console.log('🚪 서버에서 방 퇴장 완료');
      
      // 내 방 목록 새로고침
      fetchMyRooms();
    } catch (error) {
      console.error('❌ 서버 방 퇴장 실패:', error);
      // 서버 오류가 있어도 클라이언트 정리는 계속 진행
    } finally {
      // WebSocket 연결 해제
      if (socket) {
        socket.close();
      }
      
      // 모든 채팅 관련 상태 초기화
      setCurrentRoom('');
      setMessages([]);
      setMessage(''); // 입력 중이던 메시지도 초기화
      setConnected(false);
      setSocket(null);
      
      console.log('🚪 방에서 완전히 나감 (서버 + 클라이언트 정리)');
    }
  };

  // 내 방에서 나가기
  const handleLeaveMyRoom = async (roomName) => {
    if (!window.confirm(`'${roomName}' 방에서 나가시겠습니까?`)) {
      return;
    }
    
    try {
      await axios.post(`/api/rooms/${roomName}/leave/`);
      fetchMyRooms();
      alert('방에서 나갔습니다.');
    } catch (error) {
      console.error('❌ 방 나가기 실패:', error);
      alert('방 나가기에 실패했습니다.');
    }
  };

  // 뒤로가기
  const handleDisconnectRoom = () => {
    // WebSocket 연결 해제
    if (socket) {
      socket.close();
    }
    
    // 채팅 상태 초기화하여 방 목록으로 돌아가기
    setCurrentRoom('');
    setMessages([]);
    setConnected(false);
    setSocket(null);
    setMessage('');
    
    console.log('🔙 방 목록으로 돌아가기 (서버 레코드 유지)');
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
      }
    };

    initializeAuth();
  }, [setAuthToken]);

  // 데이터 로드
  useEffect(() => {
    fetchRooms();
    fetchMyRooms();
    fetchStats();
  }, [fetchRooms, fetchMyRooms, fetchStats]);

  // 🔄 정기 데이터 새로고침
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      fetchRooms();
      fetchMyRooms();
      fetchStats();
    }, 30000);

    return () => clearInterval(interval);
  }, [isAuthenticated, fetchRooms, fetchMyRooms, fetchStats]);

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

            {/* 서버 호출 포함 실제 나가기 */}
            <button onClick={handleLeaveRoom} className="btn btn-secondary">
              방 나가기
            </button>

            {/* WebSocket만 끊기 */}
            <button onClick={handleDisconnectRoom} className="btn btn-outline">
              뒤로가기
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
        <h1>Test 채팅</h1>
        <div className="header-actions">
          {/* 온라인 사용자 수 */}
          <div className="online-stats">
            <span className="stat-icon">🌱</span>
            <span className="stat-text">  {stats.online_users || 0}</span>
          </div>
          
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

        {/* 내가 입장한 채팅방 목록 */}
        {isAuthenticated && myRooms.length > 0 && (
          <section className="my-rooms-section">
            <div className="section-header">
              <h2>🏠 내가 입장한 채팅방</h2>
              <span className="room-count">{myRooms.length}개</span>
            </div>
            <div className="my-rooms-grid">
              {myRooms.map(room => (
                <div key={room.id} className="my-room-card">
                  <h3 className="room-name">{room.name}</h3>
                  <p className="room-description">{room.description}</p>
                  <div className="room-info">
                    <span className="room-members">
                      👥 {room.member_count}/{room.max_members}
                    </span>
                    <span className="last-seen">
                      🕐 {room.last_seen ? new Date(room.last_seen).toLocaleString() : '미접속'}
                    </span>
                  </div>
                  <div className="room-actions">
                    <button 
                      className="btn btn-primary btn-sm"
                      onClick={() => handleJoinRoom(room.name)}
                    >
                      입장하기
                    </button>
                    <button 
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleLeaveMyRoom(room.name)}
                    >
                      나가기
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 방 생성 섹션 */}
        {isAuthenticated && (
          <section className="create-section">
            <div className="section-header">
              <h2>✚ 새 방 만들기</h2>
              {!showCreateRoom && (
                <button onClick={() => setShowCreateRoom(true)} className="btn btn-success btn-sm">
                  + 방 만들기
                </button>
              )}
            </div>
            
            {showCreateRoom && (
              <div className="create-form">
                <div className="form-row">
                  <input
                    type="text"
                    placeholder="방 이름"
                    value={roomForm.name}
                    onChange={(e) => setRoomForm({...roomForm, name: e.target.value})}
                    className="form-input"
                  />
                  <input
                    type="number"
                    placeholder="최대 인원"
                    value={roomForm.max_members}
                    onChange={(e) => setRoomForm({...roomForm, max_members: e.target.value})}
                    className="form-input form-input-small"
                    min="1"
                    max="1000"
                  />
                </div>
                <input
                  type="text"
                  placeholder="방 설명 (선택사항)"
                  value={roomForm.description}
                  onChange={(e) => setRoomForm({...roomForm, description: e.target.value})}
                  className="form-input"
                />
                <div className="form-actions">
                  <button onClick={() => setShowCreateRoom(false)} className="btn btn-outline btn-sm">
                    취소
                  </button>
                  <button onClick={handleCreateRoom} className="btn btn-success btn-sm">
                    생성
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {/* 모든 채팅방 목록 */}
        <section className="rooms-section">
          <h2>🌟 모든 채팅방</h2>
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