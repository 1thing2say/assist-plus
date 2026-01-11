import React from 'react';

function About() {
  return (
    <div className="container mx-auto px-6 py-16 mt-16">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-6 text-center">
          About <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">assist+</span>
        </h1>
        
        <div className="bg-white rounded-xl shadow-lg p-8 border-2 border-gray-200 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Your Transfer Journey, Simplified</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            Navigating the path from California community college to a UC can be overwhelming. 
            With thousands of course articulation agreements and constantly changing requirements, 
            knowing exactly what you need to transfer can feel impossible.
          </p>
          <p className="text-gray-700 leading-relaxed">
            <strong>assist+</strong> takes the guesswork out of transfer planning. Simply upload your 
            transcript, select your target UC school and major, and instantly see how your completed 
            courses align with official articulation agreements.
          </p>
        </div>

        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl shadow-lg p-8 border-2 border-indigo-200 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">How It Works</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center text-white font-bold shrink-0">1</div>
              <div>
                <h3 className="font-semibold text-gray-800">Upload Your Transcript</h3>
                <p className="text-gray-600">Upload your unofficial transcript PDF from your community college.</p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold shrink-0">2</div>
              <div>
                <h3 className="font-semibold text-gray-800">Set Your Transfer Goals</h3>
                <p className="text-gray-600">Choose your target UC campus and intended major from our comprehensive list.</p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-pink-600 rounded-full flex items-center justify-center text-white font-bold shrink-0">3</div>
              <div>
                <h3 className="font-semibold text-gray-800">Get Instant Results</h3>
                <p className="text-gray-600">See exactly which requirements you've satisfied and what courses you still need to complete.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-8 border-2 border-gray-200 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Supported Schools</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            We support transfers to all nine UC undergraduate campuses:
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {['UC Berkeley', 'UCLA', 'UC San Diego', 'UC Irvine', 'UC Davis', 'UC Santa Barbara', 'UC Riverside', 'UC Santa Cruz', 'UC Merced'].map((school) => (
              <div key={school} className="bg-gradient-to-r from-indigo-100 to-purple-100 px-4 py-2 rounded-lg text-center text-gray-700 font-medium">
                {school}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl shadow-lg p-8 border-2 border-purple-200">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Why assist+?</h2>
          <ul className="space-y-3 text-gray-700">
            <li className="flex items-start gap-3">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>Save hours</strong> of manual comparison between your courses and articulation agreements</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>Reduce stress</strong> with clear, visual breakdowns of your transfer progress</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>Stay on track</strong> by knowing exactly which courses to prioritize each semester</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-500 font-bold">✓</span>
              <span><strong>Built by students, for students</strong> who understand the transfer struggle firsthand</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default About;
