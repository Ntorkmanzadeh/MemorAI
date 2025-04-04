import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  TextField,
  Paper,
  CircularProgress,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  AppBar,
  Toolbar,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Upload as UploadIcon,
  ContentCopy as CopyIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import axios from 'axios';

function App() {
  // State for user management
  const [userId, setUserId] = useState(localStorage.getItem('userId') || '');
  const [userName, setUserName] = useState(localStorage.getItem('userName') || '');
  const [newUserName, setNewUserName] = useState('');
  const [showSignUp, setShowSignUp] = useState(false);

  // State for deck management
  const [decks, setDecks] = useState([]);
  const [selectedDeck, setSelectedDeck] = useState('');
  const [newDeckName, setNewDeckName] = useState('');
  const [newDeckDescription, setNewDeckDescription] = useState('');
  const [showNewDeck, setShowNewDeck] = useState(false);

  // State for flashcard management
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [flashcards, setFlashcards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // State for editing flashcards
  const [editingCard, setEditingCard] = useState(null);
  const [showEditCard, setShowEditCard] = useState(false);

  // Load decks when user changes
  useEffect(() => {
    if (userId) {
      loadDecks();
    }
  }, [userId]);

  const loadDecks = async () => {
    try {
      const response = await axios.get('http://localhost:8000/decks', {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setDecks(response.data.decks);
    } catch (err) {
      setError('Failed to load decks: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleSignUp = async () => {
    try {
      const formData = new FormData();
      formData.append('name', newUserName);
      
      const response = await axios.post('http://localhost:8000/users', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setUserId(response.data.user_id);
      setUserName(response.data.name);
      localStorage.setItem('userId', response.data.user_id);
      localStorage.setItem('userName', response.data.name);
      setShowSignUp(false);
      setSuccess('Successfully signed up!');
    } catch (err) {
      setError('Failed to sign up: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleCreateDeck = async () => {
    try {
      const formData = new FormData();
      formData.append('name', newDeckName);
      formData.append('description', newDeckDescription);
      formData.append('user_id', userId);
      
      const response = await axios.post('http://localhost:8000/decks', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      if (response.data && response.data.deck_id) {
        setDecks([...decks, {
          id: response.data.deck_id,
          name: response.data.name,
          description: response.data.description
        }]);
        setShowNewDeck(false);
        setNewDeckName('');
        setNewDeckDescription('');
        setSuccess('Deck created successfully!');
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error occurred';
      setError('Failed to create deck: ' + errorMessage);
      console.error('Deck creation error:', err);
    }
  };

  const handleDeleteDeck = async (deckId) => {
    try {
      await axios.delete(`http://localhost:8000/decks/${deckId}`);
      setDecks(decks.filter(deck => deck.id !== deckId));
      if (selectedDeck === deckId) {
        setSelectedDeck('');
        setFlashcards([]);
      }
      setSuccess('Deck deleted successfully!');
    } catch (err) {
      setError('Failed to delete deck');
    }
  };

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleTextChange = (event) => {
    setText(event.target.value);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedDeck) {
      setError('Please select a deck first');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    setFlashcards([]);

    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (text) {
      formData.append('text', text);
    }
    formData.append('deck_id', selectedDeck);
    formData.append('user_id', userId);

    try {
      const response = await axios.post('http://localhost:8000/process-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      if (response.data.flashcards && Array.isArray(response.data.flashcards)) {
        setFlashcards(response.data.flashcards);
        setSuccess('Flashcards generated successfully!');
      } else {
        setError('Invalid response format from server');
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || err.message || 'An error occurred while processing your request.';
      setError('Failed to process file: ' + errorMessage);
      console.error('Process file error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditCard = async (cardId, question, answer) => {
    try {
      const formData = new FormData();
      formData.append('question', question);
      formData.append('answer', answer);
      
      const response = await axios.put(`http://localhost:8000/flashcards/${cardId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setFlashcards(flashcards.map(card => 
        card.id === cardId ? { ...card, question, answer } : card
      ));
      setShowEditCard(false);
      setEditingCard(null);
      setSuccess('Flashcard updated successfully!');
    } catch (err) {
      setError('Failed to update flashcard: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteCard = async (cardId) => {
    try {
      await axios.delete(`http://localhost:8000/flashcards/${cardId}`);
      setFlashcards(flashcards.filter(card => card.id !== cardId));
      setSuccess('Flashcard deleted successfully!');
    } catch (err) {
      setError('Failed to delete flashcard');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
  };

  if (!userId) {
    return (
      <Container maxWidth="sm">
        <Box sx={{ my: 4, textAlign: 'center' }}>
          <Typography variant="h4" gutterBottom>
            Welcome to Flashcard Generator
          </Typography>
          <Button
            variant="contained"
            onClick={() => setShowSignUp(true)}
            sx={{ mt: 2 }}
          >
            Sign Up
          </Button>
        </Box>

        <Dialog open={showSignUp} onClose={() => setShowSignUp(false)}>
          <DialogTitle>Sign Up</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Name"
              fullWidth
              value={newUserName}
              onChange={(e) => setNewUserName(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowSignUp(false)}>Cancel</Button>
            <Button onClick={handleSignUp} variant="contained">Sign Up</Button>
          </DialogActions>
        </Dialog>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Flashcard Generator
          </Typography>
          <Typography variant="body1" sx={{ mr: 2 }}>
            Welcome, {userName}
          </Typography>
          <Button color="inherit" onClick={() => {
            setUserId('');
            setUserName('');
            localStorage.removeItem('userId');
            localStorage.removeItem('userName');
          }}>
            Sign Out
          </Button>
        </Toolbar>
      </AppBar>

      <Box sx={{ my: 4 }}>
        <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Select Deck</InputLabel>
              <Select
                value={selectedDeck}
                onChange={(e) => setSelectedDeck(e.target.value)}
                label="Select Deck"
              >
                {decks.map((deck) => (
                  <MenuItem key={deck.id} value={deck.id}>
                    {deck.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setShowNewDeck(true)}
            >
              New Deck
            </Button>
          </Box>

          <form onSubmit={handleSubmit}>
            <Box sx={{ mb: 3 }}>
              <Button
                variant="contained"
                component="label"
                startIcon={<UploadIcon />}
                sx={{ mb: 2 }}
              >
                Upload File
                <input
                  type="file"
                  hidden
                  accept=".pdf,.pptx"
                  onChange={handleFileChange}
                />
              </Button>
              {file && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Selected file: {file.name}
                </Typography>
              )}
            </Box>

            <TextField
              fullWidth
              multiline
              rows={4}
              variant="outlined"
              label="Or paste your text here"
              value={text}
              onChange={handleTextChange}
              sx={{ mb: 3 }}
            />

            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              disabled={loading || (!file && !text) || !selectedDeck}
            >
              {loading ? <CircularProgress size={24} /> : 'Generate Flashcards'}
            </Button>
          </form>
        </Paper>

        {flashcards.length > 0 && (
          <Box>
            <Typography variant="h5" gutterBottom>
              Generated Flashcards ({flashcards.length})
            </Typography>
            {flashcards.map((card) => (
              <Card key={card.id} sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Question:
                  </Typography>
                  <Typography variant="body1" paragraph>
                    {card.question}
                  </Typography>
                  <Typography variant="h6" gutterBottom>
                    Answer:
                  </Typography>
                  <Typography variant="body1">
                    {card.answer}
                  </Typography>
                </CardContent>
                <CardActions>
                  <IconButton
                    onClick={() => copyToClipboard(`Q: ${card.question}\nA: ${card.answer}`)}
                    size="small"
                  >
                    <CopyIcon />
                  </IconButton>
                  <IconButton
                    onClick={() => {
                      setEditingCard(card);
                      setShowEditCard(true);
                    }}
                    size="small"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    onClick={() => handleDeleteCard(card.id)}
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                </CardActions>
              </Card>
            ))}
          </Box>
        )}

        <Dialog open={showNewDeck} onClose={() => setShowNewDeck(false)}>
          <DialogTitle>Create New Deck</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Deck Name"
              fullWidth
              value={newDeckName}
              onChange={(e) => setNewDeckName(e.target.value)}
            />
            <TextField
              margin="dense"
              label="Description"
              fullWidth
              multiline
              rows={3}
              value={newDeckDescription}
              onChange={(e) => setNewDeckDescription(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowNewDeck(false)}>Cancel</Button>
            <Button onClick={handleCreateDeck} variant="contained">Create</Button>
          </DialogActions>
        </Dialog>

        <Dialog open={showEditCard} onClose={() => setShowEditCard(false)}>
          <DialogTitle>Edit Flashcard</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Question"
              fullWidth
              multiline
              rows={2}
              value={editingCard?.question || ''}
              onChange={(e) => setEditingCard({ ...editingCard, question: e.target.value })}
            />
            <TextField
              margin="dense"
              label="Answer"
              fullWidth
              multiline
              rows={3}
              value={editingCard?.answer || ''}
              onChange={(e) => setEditingCard({ ...editingCard, answer: e.target.value })}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowEditCard(false)}>Cancel</Button>
            <Button
              onClick={() => handleEditCard(editingCard.id, editingCard.question, editingCard.answer)}
              variant="contained"
            >
              Save
            </Button>
          </DialogActions>
        </Dialog>

        <Snackbar
          open={!!error}
          autoHideDuration={6000}
          onClose={() => setError('')}
        >
          <Alert severity="error" onClose={() => setError('')}>
            {error}
          </Alert>
        </Snackbar>

        <Snackbar
          open={!!success}
          autoHideDuration={6000}
          onClose={() => setSuccess('')}
        >
          <Alert severity="success" onClose={() => setSuccess('')}>
            {success}
          </Alert>
        </Snackbar>
      </Box>
    </Container>
  );
}

export default App; 