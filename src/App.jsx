import './App.css'
import Home from './Home'
import DocumentAnalyzer from './DocumentAnalyzer'
import About from './about'
import Results from './Results'
import { Routes, Route, Link } from 'react-router-dom'
import Footer from './Footer'

function App() {

  return (
    <div className="w-full h-screen">
      <nav className="bg-white shadow-md fixed top-0 left-0 right-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link 
              to="/" 
              className="text-2xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent hover:opacity-80 transition-opacity duration-200 cursor-pointer"
            >
              assist+
            </Link>
            <Link 
              to="/about" 
              className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center transition-colors duration-200 text-gray-700 hover:text-gray-900"
              title="About"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </Link>
          </div>
        </div>
      </nav>
      
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyzer" element={
          <div className='parent'>
            <DocumentAnalyzer/>
          </div>
        } />
        <Route path="/about" element={<About />} />
        <Route path="/results" element={<Results />} />
      </Routes>
      <Footer />
    </div>
  )
}

export default App
