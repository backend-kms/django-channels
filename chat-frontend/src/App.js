import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { subscribeUserToPush } from './subscribePush';
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams, Link } from 'react-router-dom';
import './App.css';

// API 기본 설정
const API_BASE_URL = 'http://localhost:8000/chat';
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = false;


// 1. 메시지 반응 컴포넌트
const MessageReactions = ({ messageId, currentUser, reactions: initialReactions, userReaction: initialUserReaction }) => {
  const [reactions, setReactions] = useState({
    like: 0,
    good: 0,
    check: 0,
    ...initialReactions
  });
  const [userReaction, setUserReaction] = useState(initialUserReaction);
  const [isLoading, setIsLoading] = useState(false);
  
  const reactionEmojis = {
    like: '❤️',
    good: '👍',
    check: '✅'
  };

  useEffect(() => {
    if (initialReactions) {
      setReactions(prev => ({
        like: 0,
        good: 0,
        check: 0,
        ...initialReactions
      }));
    }
  }, [initialReactions]);

  useEffect(() => {
    setUserReaction(initialUserReaction);
  }, [initialUserReaction]);

  const handleReactionClick = async (reactionType) => {
    if (isLoading) return;
    setIsLoading(true);
    setUserReaction(userReaction === reactionType ? null : reactionType);

    try {
      const response = await axios.post(`/api/messages/${messageId}/reaction/`, {
        reaction_type: reactionType
      });

      if (response.data.success) {
        const reactionCounts = response.data.reaction_counts || {};
        
        let calculatedUserReaction = null;
        if (response.data.action === 'added') {
          calculatedUserReaction = response.data.reaction_type;
        } else if (response.data.action === 'removed') {
          calculatedUserReaction = null;
        } else if (response.data.action === 'updated') {
          calculatedUserReaction = response.data.reaction_type;
        }
        
        setReactions(reactionCounts);
        setUserReaction(calculatedUserReaction);
      }
    } catch (error) {
      console.error('반응 처리 실패:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="message-reactions" data-message-id={messageId}>
      <div className="reaction-buttons">
        {Object.keys(reactionEmojis).map(reactionType => (
          <button
            key={reactionType}
            className={`reaction-btn ${userReaction === reactionType ? 'active' : ''}`}
            onClick={() => handleReactionClick(reactionType)}
            disabled={isLoading}
            title={`${reactionEmojis[reactionType]} ${reactionType}`}
          >
            <span className="reaction-emoji">
              {reactionEmojis[reactionType]}
            </span>
            {reactions[reactionType] > 0 && (
              <span className="reaction-count">
                {reactions[reactionType]}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};


// 2. ChatRoom 컴포넌트 (UI 담당)

const ChatRoom = ({
  user,
  currentRoom,
  currentRoomInfo,
  connected,
  messages,
  message,
  setMessage,
  handleSendMessage,
  handleLeaveRoom,
  handleKeyPress,
  messagesEndRef,
  selectedFile,
  isUploading,
  fileInputRef,
  handleFileSelect,
  handleFileUpload,
  handleFileDownload,
  formatFileSize,
  fetchNextMessages,
  messagePagination,
  setSelectedFile
}) => {
  const navigate = useNavigate();

  // 무한 스크롤 감지 로직
  useEffect(() => {
    const messagesContainer = document.querySelector('.chat-messages');
    if (!messagesContainer) return;

    const handleScroll = () => {
      if (messagesContainer.scrollTop === 0 && messagePagination.next) {
        fetchNextMessages();
      }
    };

    messagesContainer.addEventListener('scroll', handleScroll);
    return () => messagesContainer.removeEventListener('scroll', handleScroll);
  }, [messagePagination.next, fetchNextMessages]);

  return (
    <div className="app chat-app">
      <div className="chat-header">
        <div className="room-info">
          <h1>💬 {currentRoomInfo?.name || currentRoom}</h1>
          <div className="room-details">
            <span className={`status ${connected ? 'online' : 'offline'}`}>
              {connected ? '🟢 연결됨' : '🔴 연결 안됨'}
            </span>
            {currentRoomInfo && (
              <span className="member-count">
                {currentRoomInfo.current_members || 0}/{currentRoomInfo.max_members || 0}
              </span>
            )}
          </div>
        </div>
        <div className="header-actions">
          <span className="user-name">👋 {user?.username}</span>
          {/* '방 나가기'는 서버에서 탈퇴 */}
          <button onClick={handleLeaveRoom} className="btn btn-secondary">
            방 나가기
          </button>
          <button onClick={() => {
            // 뒤로가기는 URL 이동만 수행 (연결 해제는 Loader의 cleanup이 담당)
            navigate('/');
          }} className="btn btn-outline">
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
        ) : (() => {
          let lastDate = '';
          return messages.map((msg, idx) => {
            let dateKey = '';
            console.log( msg)
            if (msg.created_at) {
              dateKey = new Date(msg.created_at).toDateString();
            }

            const displayDate = new Date(dateKey).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
            
            const showDateLine = idx === 0 || dateKey !== lastDate;
            lastDate = dateKey;

            return (
              <React.Fragment key={msg.id}>
                {showDateLine && (
                  <div className="date-separator">
                    <span>{displayDate}</span>
                  </div>
                )}
                <div 
                  key={msg.id} 
                  className={`message ${
                    msg.isSystem ? 'system-message' : 
                    msg.author === user?.username ? 'my-message' : 'other-message'
                  }`}
                  data-message-id={msg.message_id}
                >
                  <div className="message-header">
                    <span className="author">{msg.author}</span>
                    <span className="time">{msg.time}</span>
                  </div>
                  
                  {!msg.isSystem ? (
                    <>
                      <div className="message-wrapper">
                        <div className="message-bubble">
                          {msg.isFile ? (
                            <div className="file-message">
                              {msg.isImage ? (
                                <div className="image-message">
                                  <img 
                                    src={`http://localhost:8000${msg.fileUrl}`}
                                    alt={msg.fileName}
                                    className="message-image"
                                    onClick={() => handleFileDownload(msg.fileUrl, msg.fileName)}
                                    onError={(e) => {
                                      e.target.style.display = 'none';
                                      e.target.nextSibling.style.display = 'block';
                                    }}
                                  />
                                  <div className="image-fallback" style={{display: 'none'}}>
                                    <div className="file-icon">🖼️</div>
                                    <div className="file-details">
                                      <div className="file-name">{msg.fileName}</div>
                                      <div className="file-size">{msg.fileSizeHuman}</div>
                                      <button 
                                        className="download-btn"
                                        onClick={() => handleFileDownload(msg.fileUrl, msg.fileName)}
                                      >
                                        다운로드
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="file-attachment">
                                  <div className="file-icon">📎</div>
                                  <div className="file-details">
                                    <div className="file-name">{msg.fileName}</div>
                                    <div className="file-size">{msg.fileSizeHuman}</div>
                                  </div>
                                  <button 
                                    className="download-btn"
                                    onClick={() => handleFileDownload(msg.fileUrl, msg.fileName)}
                                  >
                                    다운로드
                                  </button>
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="message-content">{msg.text}</div>
                          )}
                        </div>
                        
                        <div className="read-status">
                          {msg.author === user?.username ? (
                            msg.unreadCount > 0 && (
                              <span className="unread-count">{msg.unreadCount}</span>
                            )
                          ) : (
                            msg.isReadByAll ? (
                              <span className="read-all"></span>
                            ) : msg.unreadCount > 0 ? (
                              <span className="unread-count">{msg.unreadCount}</span>
                            ) : null
                          )}
                        </div>
                      </div>
                      
                      <MessageReactions 
                        messageId={msg.message_id}
                        currentUser={user?.username}
                        reactions={msg.reactions}
                        userReaction={msg.userReaction}
                      />
                    </>
                  ) : (
                    <div className="message-bubble">
                      <div className="message-content">{msg.text}</div>
                    </div>
                  )}
                </div>
              </React.Fragment>
            );
          });
        })()}
        <div ref={messagesEndRef} />
      </div>
    
      <div className="message-input">
        {/* 파일 선택 표시 */}
        {selectedFile && (
          <div className="selected-file">
            {selectedFile.isImage ? (
              <div className="image-preview">
                <img 
                  src={selectedFile.previewUrl} 
                  alt="미리보기"
                  className="preview-image"
                />
                <div className="file-info">
                  <span>🖼️ {selectedFile.name}</span>
                  <span>({formatFileSize(selectedFile.size)})</span>
                </div>
              </div>
            ) : (
              <div className="file-info">
                <span>📎 {selectedFile.name}</span>
                <span>({formatFileSize(selectedFile.size)})</span>
              </div>
            )}
            <button onClick={() => {
              if (selectedFile.previewUrl) {
                URL.revokeObjectURL(selectedFile.previewUrl);
              }
              setSelectedFile(null);
            }} className="remove-file">
              ❌
            </button>
          </div>
        )}
        
        <div className="input-row">
          {/* 파일 선택 버튼 */}
          <button 
            className="file-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={!connected || isUploading}
            title="파일 첨부"
          >
            📎
          </button>
          
          {/* 숨겨진 파일 입력 */}
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            accept="*/*"
          />
          
          {/* 메시지 입력 */}
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="메시지를 입력하세요..."
            disabled={!connected}
            className="message-field"
          />
          
          {/* 전송 버튼들 */}
          {selectedFile ? (
            <button 
              onClick={handleFileUpload} 
              disabled={!connected || isUploading}
              className="btn btn-primary"
            >
              {isUploading ? '업로드 중...' : '파일 전송'}
            </button>
          ) : (
            <button 
              onClick={handleSendMessage} 
              disabled={!connected || !message.trim()}
              className="btn btn-primary"
            >
              전송
            </button>
          )}
        </div>
      </div>
    </div>
  );
};


// 3. RoomList 컴포넌트 (UI 담당)
const RoomList = ({
  user,
  isAuthenticated,
  loginForm,
  setLoginForm,
  handleLogin,
  handleLogout,
  handleKeyPress,
  stats,
  rooms,
  myRooms,
  showCreateRoom,
  setShowCreateRoom,
  roomForm,
  setRoomForm,
  handleCreateRoom,
  handleJoinRoom,
  handleLeaveMyRoom
}) => {
  const navigate = useNavigate();

  // 방 입장 버튼 클릭 시: 라우팅을 위해 네비게이트 트리거
  const onJoinRoom = (roomId) => {
    navigate(`/chat/${roomId}`);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Test 채팅</h1>
        <div className="header-actions">
          <button onClick={subscribeUserToPush}>
            푸시 알림 구독하기
          </button>
          <div className="online-stats">
            <span className="stat-icon stat-text">🌱 온라인 수: </span>
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

      <main className="main-content">
        {isAuthenticated && myRooms.length > 0 && (
          <section className="my-rooms-section">
            <div className="section-header">
              <h2>🏠 내가 입장한 채팅방</h2>
              <span className="room-count">
                {myRooms.length}개
              </span>
            </div>
            <div className="my-rooms-grid">
              {myRooms
                .sort((a, b) => (b.unread_count || 0) - (a.unread_count || 0))
                .map(room => (
                <div key={room.id} className={`my-room-card ${room.unread_count > 0 ? 'has-unread' : ''}`}>
                  <div className="room-header">
                    <h3 className="room-name">
                      {room.name}
                      {room.unread_count > 0 && (<span className="unread-badge">{room.unread_count > 99 ? '99+' : room.unread_count}</span>)}
                    </h3>
                  </div>
                  <p className="room-description">{room.description}</p>
                  <div className="room-info">
                    <span className="room-members">
                      👥 인원수: {room.member_count}/{room.max_members}
                    </span>
                    <span className="last-seen">
                      🕐 마지막 접속: {room.last_seen ? new Date(room.last_seen).toLocaleString() : '미접속'}
                    </span>
                  </div>
                  <div className="room-actions">
                    <button 
                      className={`btn btn-sm ${room.unread_count > 0 ? 'btn-primary btn-glow' : 'btn-primary'}`}
                      onClick={() => onJoinRoom(room.id)}
                    >
                      {room.unread_count > 0 ? `⚡ 새 메시지 ${room.unread_count}개` : '열기'}
                    </button>
                    <button 
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleLeaveMyRoom(room.id)}
                    >
                      나가기
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

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
                      onClick={() => onJoinRoom(room.id)}
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
};



// 4. AppWrapper 컴포넌트 (모든 상태와 로직 관리)

function AppWrapper() {
  const navigate = useNavigate();
  
  // 상태 정의
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [rooms, setRooms] = useState([]);
  const [myRooms, setMyRooms] = useState([]);
  const [stats, setStats] = useState({});
  const [currentRoom, setCurrentRoom] = useState(''); // 현재 방 ID
  const [currentRoomInfo, setCurrentRoomInfo] = useState(null);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [socket, setSocket] = useState(null);
  const globalSocketRef = useRef(null); 
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [connected, setConnected] = useState(false);
  const messagesEndRef = useRef(null);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [roomForm, setRoomForm] = useState({ name: '', description: '', max_members: 100 });
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);
  const [messagePagination, setMessagePagination] = useState({
    next: null,
    previous: null,
    count: 0,
    currentPage: 1,
    pageSize: 30
  });
  // const [isJoining, setIsJoining] = useState(false);

  const fetchNextMessages = useCallback(async () => {
  if (!messagePagination.next) return;
  const nextUrl = messagePagination.next.replace(API_BASE_URL, '');
  const response = await axios.get(nextUrl);
  if (response.data && response.data.results) {
    const moreMessages = response.data.results.map(msg => ({
      id: msg.id,
      message_id: msg.id,
      text: msg.content || msg.message,
      author: msg.username || 'Anonymous',
      created_at: msg.created_at,
      time: new Date(msg.created_at).toLocaleTimeString(),
      isSystem: msg.message_type === 'system',
      isFile: msg.message_type === 'file' || msg.message_type === 'image',
      isImage: msg.is_image || msg.message_type === 'image',
      messageType: msg.message_type,
      fileName: msg.file_name,
      fileSize: msg.file_size,
      fileSizeHuman: msg.file_size_human,
      fileUrl: msg.file,             
      unreadCount: msg.unread_count || 0,
      isReadByAll: msg.is_read_by_all || false,
      userId: msg.user_id,
      reactions: msg.reactions || {},
      userReaction: msg.user_reaction || null
    })).reverse();
    setMessages(prev => [...moreMessages, ...prev]);
    setMessagePagination(prev => ({
      ...prev,
      next: response.data.next,
      previous: response.data.previous,
      currentPage: prev.currentPage + 1
    }));
  }
}, [messagePagination.next]);

  const setAuthToken = useCallback((token) => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('access_token', token);
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  }, []);

  const connectGlobalSocket = useCallback((user) => {
    // 이전 연결이 있으면 닫고 참조를 해제하여 핸들러 누적을 막습니다.
    if (globalSocketRef.current) {
      globalSocketRef.current.close();
      globalSocketRef.current = null;
    }
    
    const ws = new WebSocket(`ws://localhost:8000/ws/global/${user.id}/`);
    ws.onopen = () => {
      console.log('글로벌 WebSocket 연결됨');
      globalSocketRef.current = ws;
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'unread_count_update') {
        
        setMyRooms(prevRooms => 
          prevRooms.map(room => 
            parseInt(room.id) === parseInt(data.room_id)
              ? { ...room, unread_count: data.unread_count }
              : room
          )
        );
      } else if (data.type === 'all_unread_counts') {
        setMyRooms(prevRooms => 
          prevRooms.map(room => ({
            ...room,
            unread_count: data.unread_counts[room.id] || 0
          }))
        );
      } else if (data.type === 'room_created') {
        if (data.room && data.room.deactivated) {
          setRooms(prevRooms => prevRooms.filter(room => room.id !== data.room.id));
          setMyRooms(prevRooms => prevRooms.filter(room => room.id !== data.room.id));
          return;
        }
        if (data.room && data.room.id) {
          setRooms(prevRooms => {
            if (prevRooms.some(room => room.id === data.room.id)) {
              return prevRooms;
            }
            return [data.room, ...prevRooms];
          });
        }
      } else if (data.type === 'online_stats') {
        setStats(prev => ({
          ...prev,
          online_users: data.online_users
        }));
      } else if (data.type === 'room_member_update') {
        console.log("room_member_update 수신", data);
        setRooms(prevRooms =>
          prevRooms.map(room =>
            room.id === data.room_id
              ? { ...room, member_count: data.member_count }
              : room
          )
        );
        setMyRooms(prevRooms =>
          prevRooms.map(room =>
            room.id === data.room_id
              ? { ...room, member_count: data.member_count }
              : room
          )
        );
      }
    };
    ws.onclose = () => {
      console.log('글로벌 WebSocket 연결 해제됨');
      globalSocketRef.current = null;
    };
    ws.onerror = (error) => {
      console.error('글로벌 WebSocket 오류:', error);
    };
  }, []); 

  const disconnectGlobalSocket = useCallback(() => {
    if (globalSocketRef.current) {
      globalSocketRef.current.close();
      globalSocketRef.current = null;
    }
  }, []);

  const fetchRooms = useCallback(async () => {
    try {
      const response = await axios.get('/api/rooms/');
      if (response.data.results) {
        setRooms(response.data.results);
      }
    } catch (error) {
      console.error('방 목록 로드 실패:', error);
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
    } catch (error) {
      console.error('내 방 목록 로드 실패:', error);
      setMyRooms([]);
    }
  }, [isAuthenticated]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get('/api/stats/');
      if (response.data.success) {
        setStats(response.data.stats);
      }
    } catch (error) {
      console.error('통계 로드 실패:', error);
    }
  }, []);

  const fetchCurrentRoomInfo = useCallback(async (roomId) => {
    if (!roomId || !isAuthenticated) return;
    try {
      const response = await axios.get(`/api/rooms/${roomId}/info/`);
      if (response.data.success) {
        setCurrentRoomInfo(response.data.room);
      }
    } catch (error) {
      console.error('현재 방 정보 로드 실패:', error);
    }
  }, [isAuthenticated]);

  const markAsRead = useCallback(async (roomId) => {
    if (!roomId || !isAuthenticated) return;
    try {
      await axios.post(`/api/rooms/${roomId}/mark-read/`);
        setMyRooms(prevRooms => 
          prevRooms.map(room => 
            room.id === roomId 
              ? { ...room, unread_count: 0 }
              : room
          )
        );
    } catch (error) {
      console.error('읽음 처리 실패:', error);
    }
  }, [isAuthenticated]);

  const handleMessagesReadCountUpdate = useCallback((updatedMessages, readerUsername) => {
    setMessages(prevMessages => {
      return prevMessages.map(msg => {
        const updatedMsg = updatedMessages.find(um => um.id === msg.message_id);
        if (updatedMsg) {
          return {
            ...msg,
            unreadCount: updatedMsg.unread_count,
            isReadByAll: updatedMsg.is_read_by_all
          };
        }
        return msg;
      });
    });
  }, []);

  const handleReactionUpdate = useCallback((data) => {
    console.log('3. WebSocket 반응 업데이트:', data);
    setMessages(prevMessages => {
      return prevMessages.map(msg => {
        if (msg.message_id === data.message_id) {
          return {
            ...msg,
            reactions: data.reaction_counts,
            reactionType: data.reaction_type,
            lastReactionUpdate: Date.now()
          };
        }
        return msg;
      });
    });
  }, []);

  const handleChatMessage = (data) => {
    const newMessage = {
      id: data.message_id || Date.now() + Math.random(),
      message_id: data.message_id,
      text: data.message,
      author: data.username,
      created_at: data.timestamp,
      time: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
      isSystem: false,
      unreadCount: data.unread_count || 0,
      isReadByAll: data.is_read_by_all || false,
      userId: data.user_id,
      reactions: {}
    };
    setMessages(prev => {
    if (prev.some(msg => msg.message_id === newMessage.message_id)) {
      return prev;
    }
    return [...prev, newMessage];
  });
    setTimeout(() => markAsRead(currentRoom), 100);
    if (data.username !== user?.username) {
      setMyRooms(prevRooms => 
        prevRooms.map(room => {
          if (room.id === currentRoom) {
            return {
              ...room,
              last_message: data.message,
              last_message_time: new Date().toISOString()
            };
          } else {
            return room;
          }
        })
      );
    }
  };

  const handleFileMessage = (data) => {
    const newMessage = {
      id: data.message_id || Date.now() + Math.random(),
      message_id: data.message_id,
      text: data.content || data.file_name || "파일",
      author: data.username,
      time: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
      isSystem: false,
      isFile: true,
      isImage: data.is_image || data.message_type === 'image',
      messageType: data.message_type,
      fileName: data.file_name || '알 수 없는 파일',
      fileSize: data.file_size || 0,
      fileSizeHuman: data.file_size_human || '0 B',
      fileUrl: data.file_url || '',
      unreadCount: 0,
      isReadByAll: false,
      userId: data.user_id,
      reactions: {}
    };
    setMessages(prev => [...prev, newMessage]);
    setTimeout(() => markAsRead(currentRoom), 100);
  };

  const handleSystemMessage = (data, roomId) => {
    const systemMessage = {
      id: Date.now() + Math.random(),
      text: data.message,
      author: data.username,
      time: new Date().toLocaleTimeString(),
      isSystem: true,
      unreadCount: 0,
      isReadByAll: true,
      userId: null,
      reactions: {}
    };
    setMessages(prev => [...prev, systemMessage]);
    if (data.message.includes('입장') || data.message.includes('퇴장')) {
      setTimeout(() => fetchCurrentRoomInfo(roomId), 500);
    }
  };

  const handleLogin = async () => {
    try {
      if (!loginForm.username.trim() || !loginForm.password.trim()) {
        alert('아이디와 비밀번호를 입력해주세요.');
        return;
      }
      const response = await axios.post('/api/auth/login/', loginForm);
      if (response.data.success) {
        const { access_token, refresh_token, user, message } = response.data;
        setAuthToken(access_token);
        localStorage.setItem('refresh_token', refresh_token);
        localStorage.setItem('user', JSON.stringify(user));
        setUser(user);
        setIsAuthenticated(true);
        setLoginForm({ username: '', password: '' });
        alert(message);
        connectGlobalSocket(user);
        fetchRooms();
        fetchMyRooms();
        fetchStats();
      }
    } catch (error) {
      console.error('로그인 실패:', error);
      const errorMessage = error.response?.data?.error || '로그인에 실패했습니다.';
      alert(errorMessage);
    }
  };

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await axios.post('/api/auth/logout/', { refresh_token: refreshToken });
      }
    } catch (error) {
      console.error('로그아웃 API 오류:', error);
    } finally {
      if (socket) {
        socket.close();
      }
      disconnectGlobalSocket();
      setAuthToken(null);
      setUser(null);
      setIsAuthenticated(false);
      setCurrentRoom('');
      setCurrentRoomInfo(null);
      setMessages([]);
      setConnected(false);
      setSocket(null);
      setMyRooms([]);
      navigate('/');
      fetchRooms();
      fetchStats();
    }
  };

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
      const response = await axios.post('/api/rooms/create/', roomForm);
      if (response.data.success) {
        alert(response.data.message);
        setShowCreateRoom(false);
        setRoomForm({ name: '', description: '', max_members: 100 });
        fetchRooms();
        fetchMyRooms();
      }
    } catch (error) {
      console.error('방 생성 실패:', error);
      const errorMessage = error.response?.data?.error || '방 생성에 실패했습니다.';
      alert(errorMessage);
    }
  };

  // handleJoinRoom (방 입장 로직)
  const handleJoinRoom = async (targetRoomId) => {
    // 중복 호출 방지 로직
    // if (isJoining) { // isJoining 상태가 AppWrapper에 정의되지 않아 주석 처리됨.
    //   console.log('이미 방 입장 시도 중입니다. (중복 호출 방지)');
    //   return false;
    // }

    // setIsJoining(true); // 접속 시작 시 잠금 설정
    
    try {
      if (!isAuthenticated) {
        alert('로그인이 필요합니다.');
        return false; 
      }
      if (currentRoom === targetRoomId && connected) {
        return true;
      }
      if (socket) {
        socket.close();
      }

      // 로딩 UI를 위한 상태 초기화
      setCurrentRoom(targetRoomId);
      setCurrentRoomInfo(null);
      setMessages([]);
      setConnected(false);

      console.log('1. 방 입장 시도:', targetRoomId);
      const joinResponse = await axios.post(`/api/rooms/${targetRoomId}/join/?page=1&page_size=30`);
      
      if (joinResponse.data.success) {
        console.log('2. 서버 입장 성공');
        const isFirstJoin = joinResponse.data.is_first;
        
        const messagesResponse = await axios.get(`/api/rooms/${targetRoomId}/messages/`);
        if (messagesResponse.data) {
          const loadedMessages = messagesResponse.data.results.map(msg => ({
            id: msg.id,
            message_id: msg.id,
            text: msg.content || msg.message,
            author: msg.username || 'Anonymous',
            created_at: msg.created_at,
            time: new Date(msg.created_at).toLocaleTimeString(),
            isSystem: msg.message_type === 'system',
            isFile: msg.message_type === 'file' || msg.message_type === 'image',
            isImage: msg.is_image || msg.message_type === 'image',
            messageType: msg.message_type,
            fileName: msg.file_name,
            fileSize: msg.file_size,
            fileSizeHuman: msg.file_size_human,
            fileUrl: msg.file,             
            unreadCount: msg.unread_count || 0,
            isReadByAll: msg.is_read_by_all || false,
            userId: msg.user_id,
            reactions: msg.reactions || {},
            userReaction: msg.user_reaction || null
          })).reverse(); 
          setMessages(loadedMessages);

          setMessagePagination({
            next: messagesResponse.data.next,
            previous: messagesResponse.data.previous,
            count: messagesResponse.data.count,
            currentPage: 1,
            pageSize: 30
          });

          setTimeout(() => markAsRead(targetRoomId), 300);
        }

        setMyRooms(prevRooms => 
          prevRooms.map(room => 
            room.id === targetRoomId 
              ? { ...room, unread_count: 0 }
              : room
          )
        );

        setCurrentRoomInfo(joinResponse.data.room);
        
        const ws = new WebSocket(`ws://localhost:8000/ws/chat/${targetRoomId}/`);
        ws.onopen = () => {
          console.log('3. WebSocket 연결됨');
          setSocket(ws);
          setConnected(true);
          if (isFirstJoin) {
            ws.send(JSON.stringify({
              type: 'user_join',
              username: user?.username,
            }));
          }
          if (globalSocketRef.current && globalSocketRef.current.readyState === WebSocket.OPEN) {
            globalSocketRef.current.send(JSON.stringify({
              type: 'refresh_unread_counts'
            }));
          }
        };
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'messages_read_count_update') {
            handleMessagesReadCountUpdate(data.updated_messages, data.reader_username);
          } else if (data.type === 'chat') {
            handleChatMessage(data);
          } else if (data.type === 'system') {
            handleSystemMessage(data, targetRoomId);
          } else if (data.type === 'reaction_update') {
            handleReactionUpdate(data);
          } else if (data.type === 'file') { 
            handleFileMessage(data);
          }
        };
        ws.onclose = () => {
          console.log('WebSocket 연결 해제됨');
          setSocket(null);
          setConnected(false);
        };
        ws.onerror = (error) => {
          console.error('WebSocket 오류:', error);
        };

        fetchMyRooms();
        return true; 
      }
    } catch (error) {
      console.error('방 입장 실패:', error);
      setCurrentRoom(''); // 실패 시 상태 초기화
      setCurrentRoomInfo(null);
      if (error.response?.status === 404) {
        alert('존재하지 않는 채팅방입니다.');
      } else if (error.response?.status === 400) {
        alert(error.response?.data?.error || '방이 가득 찼습니다.');
      } else {
        alert(error.response?.data?.error || error.response?.data?.detail || '방 입장에 실패했습니다.');
      }
      return false; 
    } 
    // finally { // isJoining 상태가 AppWrapper에 정의되지 않아 주석 처리됨.
    //   setIsJoining(false); // 함수 종료 시 잠금 해제
    // }
  };

  const handleSendMessage = () => {
    if (socket && message.trim() && connected) {
      socket.send(JSON.stringify({
        type: 'text',
        message: message.trim(),
        username: user?.username
      }));
      setMessage('');
      setTimeout(() => markAsRead(currentRoom), 100);
    } else if (!connected) {
      alert('채팅방에 연결되지 않았습니다.');
    }
  };

  const handleLeaveRoom = async () => {
    if (!currentRoom) return;
    if (!window.confirm(`'${currentRoomInfo?.name || currentRoom}' 방에서 나가시겠습니까?`)) {
      return;
    }
    const leavingRoomId = currentRoom;
    try {
      if (socket && connected) {
        socket.send(JSON.stringify({
          type: 'user_leave',
          username: user?.username,
        }));
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      await axios.post(`/api/rooms/${leavingRoomId}/leave/`);
      fetchMyRooms();
    } catch (error) {
      console.error('서버 방 퇴장 실패:', error);
    } finally {
      if (socket) {
        socket.close();
      }
      setCurrentRoom('');
      setCurrentRoomInfo(null);
      setMessages([]);
      setConnected(false);
      setSocket(null);
      navigate('/'); // 메인 화면으로 이동
    }
  };

  const handleLeaveMyRoom = async (roomId) => {
    if (!window.confirm(`'${roomId}' 방에서 나가시겠습니까?`)) {
      return;
    }
    try {
      if (currentRoom === roomId && socket && connected) {
        socket.send(JSON.stringify({
          type: 'user_leave',
          username: user?.username
        }));
        await new Promise(resolve => setTimeout(resolve, 100));
        await axios.post(`/api/rooms/${roomId}/leave/`);
        if (socket) {
          socket.close();
        }
        setCurrentRoom('');
        setCurrentRoomInfo(null);
        setMessages([]);
        setMessage('');
        setConnected(false);
        setSocket(null);
        navigate('/'); 
      } else {
        const tempWs = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}/`);
        tempWs.onopen = () => {
          tempWs.send(JSON.stringify({
            type: 'user_leave',
            username: user?.username
          }));
          setTimeout(() => {
            tempWs.close();
          }, 200);
        };
        await axios.post(`/api/rooms/${roomId}/leave/`);
      }
      fetchMyRooms();
      alert('방에서 나갔습니다.');
    } catch (error) {
      console.error('방 나가기 실패:', error);
      alert('방 나가기에 실패했습니다.');
    }
  };

  // handleDisconnectRoom (연결만 해제하고 상태 초기화)
  const handleDisconnectRoom = async () => {
    const roomId = currentRoom;
    try {
      if (roomId && isAuthenticated) {
        await axios.post(`/api/rooms/${roomId}/disconnect/`);
      }
    } catch (error) {
      console.error('서버 연결 해제 알림 실패:', error);
    }

    if (socket) {
      socket.close();
    }
    
    // 상태만 초기화 (라우터가 네비게이션을 담당)
    setCurrentRoom('');
    setCurrentRoomInfo(null);
    setMessages([]);
    setConnected(false);
    setSocket(null);
    setMessage('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      if (!isAuthenticated) {
        handleLogin();
      } else if (currentRoom) {
        handleSendMessage();
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const isImageFile = (fileName) => {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
    return imageExtensions.some(ext => fileName.toLowerCase().endsWith(ext));
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        alert('파일 크기는 10MB를 초과할 수 없습니다.');
        return;
      }
      if (isImageFile(file.name)) {
        const previewUrl = URL.createObjectURL(file);
        file.previewUrl = previewUrl;
        file.isImage = true;
      } else {
        file.isImage = false;
      }
      setSelectedFile(file);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !currentRoom || isUploading) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      const response = await axios.post(`/api/rooms/${currentRoom}/upload/`, formData, {
        onUploadProgress: (progressEvent) => {
          // const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        }
      });
      if (response.data.success) {
        if (selectedFile.previewUrl) {
          URL.revokeObjectURL(selectedFile.previewUrl);
        }
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    } catch (error) {
      console.error('파일 업로드 실패:', error);
      alert(error.response?.data?.error || '파일 업로드에 실패했습니다.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileDownload = (fileUrl, fileName) => {
    const link = document.createElement('a');
    link.href = `http://localhost:8000${fileUrl}`;
    link.download = fileName;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  // useEffect들 - 라이프사이클 및 상태 동기화
  
  // 1. 초기화 및 인증 확인
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');
        
        if (token && savedUser) {
          setAuthToken(token);
          const userData = JSON.parse(savedUser);
          setUser(userData);
          setIsAuthenticated(true);

          try {
            await axios.get('/api/auth/profile/');
            connectGlobalSocket(userData);
          } catch (error) {
            setAuthToken(null);
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      } catch (error) {
        console.error('인증 초기화 실패:', error);
        setAuthToken(null);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };
    initializeAuth();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

  // 2. 데이터 로드 (초기화 후)
  useEffect(() => {
    fetchRooms();
    fetchMyRooms();
    fetchStats();
  }, [fetchRooms, fetchMyRooms, fetchStats]);

  // 3. WebSocket 정리 (컴포넌트 언마운트 시)
  useEffect(() => {
    return () => {
      if (socket) {
        socket.close();
      }
      if (globalSocketRef.current) {
        globalSocketRef.current.close();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 4. 읽음 처리 (채팅창 활성화 시)
  useEffect(() => {
    if (currentRoom && isAuthenticated) {
      markAsRead(currentRoom);
    }
  }, [currentRoom, isAuthenticated, markAsRead]);

  // 5. 자동 스크롤 (메시지 변경 시)
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "instant" });
    }
  }, [messages]);

  // 6. 파일 미리보기 URL 해제 (클린업)
  useEffect(() => {
    return () => {
      if (selectedFile?.previewUrl) {
        URL.revokeObjectURL(selectedFile.previewUrl);
      }
    };
  }, [selectedFile]);

  // 모든 상태와 핸들러를 자식 컴포넌트에 props로 전달
  const commonProps = {
    user, isAuthenticated, loginForm, setLoginForm, handleLogin, handleLogout, handleKeyPress,
    stats, rooms, myRooms, showCreateRoom, setShowCreateRoom, roomForm, setRoomForm, handleCreateRoom,
    handleJoinRoom, handleLeaveRoom, handleLeaveMyRoom, handleDisconnectRoom, 
    currentRoom, currentRoomInfo, connected, messages, message,
    setMessage, handleSendMessage, messagesEndRef,
    selectedFile, setSelectedFile, isUploading, fileInputRef, handleFileSelect, handleFileUpload,
    handleFileDownload, formatFileSize, fetchNextMessages, messagePagination
  };

  // 로딩 화면
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

  return (
    <Routes>
      <Route path="/" element={<RoomList {...commonProps} />} />
      {/* ChatRoomLoader는 URL 파라미터 감지 및 접속 로직을 담당합니다. */}
      <Route path="/chat/:roomId" element={<ChatRoomLoader {...commonProps} />} />
      <Route path="*" element={
        <div className="app">
          <div className="error-container">
            <h2>404 - 페이지를 찾을 수 없습니다</h2>
            <Link to="/" className="btn btn-primary" style={{ marginTop: '20px' }}>메인으로 돌아가기</Link>
          </div>
        </div>
      } />
    </Routes>
  );
}


// 5. ChatRoomLoader (URL 파라미터 감지 및 로직 트리거)

const ChatRoomLoader = (props) => {
  const {
    isLoading,
    isAuthenticated,
    user,
    currentRoom,
    connected,
    currentRoomInfo,
    handleJoinRoom,
    handleDisconnectRoom
  } = props;

  // useParams는 <Route> 내부에서 호출되어야 파라미터를 읽을 수 있습니다.
  const { roomId: urlRoomId } = useParams();
  const navigate = useNavigate();

  // URL 감지 및 방 입장/퇴장 로직
  useEffect(() => {
    // 1. 초기 인증 로딩 중이면 대기
    if (isLoading) {
      return; 
    }

    // 2. 로딩이 끝났는데, URL ID가 있고, 인증이 안됐으면
    if (urlRoomId && !isAuthenticated) {
      alert('채팅방에 접속하려면 로그인이 필요합니다.');
      navigate('/');
      return;
    }

    // 3. 인증이 완료됐고, URL ID가 유효하며, 접속 시도가 필요할 때
    if (urlRoomId && isAuthenticated && (urlRoomId !== currentRoom || !connected)) {
      console.log('ChatRoomLoader: URL 감지 및 방 입장 시도:', urlRoomId);
      handleJoinRoom(urlRoomId);
    }

    // 4. 컴포넌트가 언마운트될 때 (페이지 이탈 시) 정리
    return () => {
      // 페이지를 떠날 때(예: '/'로 이동), 현재 연결된 상태라면 연결 해제
      if (connected) {
        console.log('ChatRoomLoader: 페이지 이탈, 연결 해제...');
        handleDisconnectRoom();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlRoomId, isAuthenticated, isLoading, user, currentRoom, connected]); 

  // --- 렌더링 로직 ---

  // 1. 방 정보가 로드 중일 때 (handleJoinRoom이 실행되었으나 currentRoomInfo가 아직 null)
  if (!currentRoomInfo || currentRoom !== urlRoomId) {
    return (
      <div className="app">
        <div className="loading-container">
          <div className="spinner"></div>
          <h2>채팅방 연결 중...</h2>
          <Link to="/" className="btn btn-secondary" style={{ marginTop: '20px' }}>메인으로 돌아가기</Link>
        </div>
      </div>
    );
  }

  // 2. 로드 완료: ChatRoom 렌더링
  return <ChatRoom {...props} />;
};


// 6. App 컴포넌트 (라우터 제공)
function App() {
  return (
    <Router>
      <AppWrapper />
    </Router>
  );
}

export default App;