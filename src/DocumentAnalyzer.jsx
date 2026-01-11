import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './index.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const DocumentAnalyzer = ({ expandedView = false }) => {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [targetUniversity, setTargetUniversity] = useState('UC Berkeley');
  const [targetMajor, setTargetMajor] = useState('Computer Science');

  const handleAnalyze = async () => {
    if (!file) return alert("Please select a file first.");
    
    setLoading(true);

    try {
      // Create FormData to send file and form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('university', targetUniversity);
      formData.append('major', targetMajor);

      // Send to Flask API
      const response = await fetch(`${API_BASE_URL}/api/analyze-transcript`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze transcript');
      }

      const data = await response.json();
      
      // Create summary text from student courses
      const courseSummary = data.student_courses
        .map(c => `${c.course_code}: ${c.course_name} (${c.credits} credits, Grade: ${c.grade})`)
        .join('\n');
      
      const summaryText = `Transcript Analysis Complete!\n\nFound ${data.student_courses.length} courses:\n${courseSummary}\n\nFound ${data.agreements.length} matching agreements.`;
      
      // Create analysis boxes for display
      const boxes = [
        {
          type: 'Summary',
          title: '📋 Transcript Summary',
          content: `Successfully extracted ${data.student_courses.length} courses from your transcript.`,
          color: 'bg-green-50 border-blue-200'
        },
        {
          type: 'Agreements',
          title: '🎓 Agreement Matches',
          content: `Found ${data.agreements.length} articulation agreement(s) matching your target: ${targetMajor} at ${targetUniversity}.`,
          color: 'bg-purple-50 border-purple-200'
        }
      ];
      
      // Navigate to results page with the data
      navigate('/results', {
        state: {
          response: summaryText,
          analysisBoxes: boxes,
          targetUniversity: targetUniversity,
          targetMajor: targetMajor,
          studentCourses: data.student_courses,
          agreements: data.agreements,
          detectedCollege: data.detected_college
        }
      });
    } catch (error) {
      console.error("Error analyzing document:", error);
      const errorMessage = "Error: " + error.message;
      
      // Navigate to results page with error
      navigate('/results', {
        state: {
          response: errorMessage,
          analysisBoxes: [{
            type: 'Error',
            title: '❌ Error',
            content: error.message,
            color: 'bg-red-50 border-red-200'
          }],
          targetUniversity: targetUniversity,
          targetMajor: targetMajor
        }
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Inline Boxes: Upload Transcript and Transfer Goals */}
      <div className="flex flex-col md:flex-row gap-6 items-stretch max-w-3xl mx-auto">
        {/* First Box: Upload Transcript */}
        <div className="flex-1 p-8 bg-gradient-to-br from-purple-100 to-pink-100 border-2 border-purple-300 rounded-[40px] shadow-2xl transition-all duration-700 ease-in-out hover:border-purple-400 hover:shadow-purple-200/50 animate-slide-left delay-300">
          <h2 className="text-4xl font-bold mb-6 text-center text-gray-800">Upload Transcript</h2>
          
          {/* File Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select a file
            </label>
            <input 
              className="w-full px-4 py-3 bg-indigo-100 border-2 border-indigo-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 hover:border-indigo-400"
              type="file" 
              accept=".pdf, .txt, .csv, application/pdf, text/plain"
              onChange={(e) => setFile(e.target.files[0])} 
              disabled={loading}
            />
          </div>
        </div>

        {/* Second Box: Target School and Major - Compact */}
        <div className="flex-1 p-6 bg-gradient-to-br from-indigo-100 to-blue-100 border-2 border-indigo-300 rounded-[40px] shadow-2xl transition-all duration-700 ease-in-out hover:border-indigo-400 hover:shadow-indigo-200/50 animate-slide-right delay-300">
          <h2 className="text-2xl font-bold mb-4 text-center text-gray-800">Transfer Goals</h2>
          
          {/* Target University */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              University
            </label>
            <select 
              value={targetUniversity}
              onChange={(e) => setTargetUniversity(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3 text-base bg-white border-2 border-indigo-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all hover:border-indigo-400"
            >
              <option>UC Berkeley</option>
              <option>UCLA</option>
              <option>UC San Diego</option>
              <option>UC Irvine</option>
              <option>UC Davis</option>
              <option>UC Santa Barbara</option>
              <option>UC Riverside</option>
              <option>UC Santa Cruz</option>
              <option>UC Merced</option>
            </select>
          </div>

          {/* Target Major */}
          <div className="mb-0">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Major
            </label>
            <select 
              value={targetMajor}
              onChange={(e) => setTargetMajor(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3 text-base bg-white border-2 border-indigo-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all hover:border-indigo-400"
            >
              <option>Computer Science</option>
              <option>Biology</option>
              <option>Business</option>
              <option>Engineering</option>
              <option>Psychology</option>
              <option>Economics</option>
              <option>Mathematics</option>
              <option>Chemistry</option>
              <option>Physics</option>
              <option>English</option>
            </select>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-center">
        <button 
          onClick={handleAnalyze} 
          disabled={loading || !file}
          className={`px-12 py-4 rounded-xl font-semibold text-white shadow-lg transition-all duration-200 text-lg animate-bounce-in delay-500 ${
            loading || !file
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-700 hover:via-purple-700 hover:to-pink-700 hover:shadow-xl transform hover:-translate-y-0.5 active:translate-y-0'
          }`}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Analyzing...
            </span>
          ) : (
            'Submit'
          )}
        </button>
      </div>
    </div>
  );
};

export default DocumentAnalyzer;