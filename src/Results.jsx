import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import './index.css';

// Helper to parse *bold* markdown
const parseMarkdown = (text) => {
  if (!text) return text;
  const parts = text.split(/(\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('*') && part.endsWith('*')) {
      return <strong key={i}>{part.slice(1, -1)}</strong>;
    }
    return part;
  });
};

function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const { 
    response, 
    analysisBoxes, 
    targetUniversity: navUniversity, 
    targetMajor: navMajor, 
    studentCourses, 
    agreements,
    detectedCollege 
  } = location.state || {};
  
  const [selectedAgreementIdx, setSelectedAgreementIdx] = useState(0);
  const [recommendations, setRecommendations] = useState('');
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsError, setRecsError] = useState('');

  // Calculate actual progress from the first agreement
  const primaryAgreement = agreements?.[selectedAgreementIdx];
  const comparison = primaryAgreement?.comparison || {};
  const courseProgress = comparison.course_progress_percentage || 0;
  const completedCount = comparison.completed_required?.length || 0;
  const totalRequired = comparison.total_required || 0;
  const groupResults = comparison.group_results || {};
  const totalGroups = comparison.total_groups || 0;
  const satisfiedGroups = comparison.satisfied_groups || 0;

  // Calculate GPA from student courses
  const calculateGPA = (courses) => {
    if (!courses || courses.length === 0) return { gpa: 0, totalUnits: 0, gradePoints: 0 };
    
    const gradePoints = {
      'A+': 4.0, 'A': 4.0, 'A-': 3.7,
      'B+': 3.3, 'B': 3.0, 'B-': 2.7,
      'C+': 2.3, 'C': 2.0, 'C-': 1.7,
      'D+': 1.3, 'D': 1.0, 'D-': 0.7,
      'F': 0.0
    };
    
    let totalPoints = 0;
    let totalUnits = 0;
    let gradedCourses = 0;
    
    courses.forEach(course => {
      const grade = course.grade?.toUpperCase();
      const credits = parseFloat(course.credits) || 0;
      
      if (grade && gradePoints[grade] !== undefined && credits > 0) {
        totalPoints += gradePoints[grade] * credits;
        totalUnits += credits;
        gradedCourses++;
      }
    });
    
    return {
      gpa: totalUnits > 0 ? (totalPoints / totalUnits).toFixed(2) : 0,
      totalUnits: totalUnits,
      gradePoints: totalPoints.toFixed(1),
      gradedCourses
    };
  };

  const gpaData = calculateGPA(studentCourses);

  // Fetch AI recommendations
  const fetchRecommendations = async () => {
    if (!primaryAgreement || loadingRecs || recommendations) return;
    
    setLoadingRecs(true);
    setRecsError('');
    
    try {
      const response = await fetch('http://localhost:5000/api/generate-recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_courses: studentCourses || [],
          completed_requirements: comparison.completed_required || [],
          missing_requirements: comparison.missing_required || [],
          target_university: primaryAgreement?.receiving_university || navUniversity,
          target_major: primaryAgreement?.major || navMajor,
          gpa: gpaData.gpa,
          progress_percentage: courseProgress,
          detected_college: detectedCollege
        })
      });
      
      const data = await response.json();
      if (data.success && data.recommendations) {
        setRecommendations(data.recommendations);
      } else {
        setRecsError(data.error || 'Failed to generate recommendations');
      }
    } catch (err) {
      setRecsError('Could not connect to AI advisor');
    } finally {
      setLoadingRecs(false);
    }
  };

  // If no results data, redirect to home
  useEffect(() => {
    if (!agreements || agreements.length === 0) {
    if (!response && (!analysisBoxes || analysisBoxes.length === 0)) {
      navigate('/');
    }
    }
  }, [response, analysisBoxes, agreements, navigate]);

  // Auto-fetch recommendations when page loads
  useEffect(() => {
    if (primaryAgreement && !recommendations && !loadingRecs) {
      fetchRecommendations();
    }
  }, [primaryAgreement]);

  // If no results data, show nothing while redirecting
  if (!agreements || agreements.length === 0) {
  if (!response && (!analysisBoxes || analysisBoxes.length === 0)) {
    return null;
  }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-12 pt-24">
        <div className="max-w-7xl mx-auto">
          
          {/* Header Section */}
          <div className="text-center mb-10 animate-slide-up">
            <h1 className="text-5xl font-black bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent mb-3">
              Transfer Analysis Complete
          </h1>
            {detectedCollege && (
              <p className="text-xl text-gray-600">
                <span className="font-semibold text-indigo-600">{detectedCollege}</span> → <span className="font-semibold">{navUniversity || 'UC Berkeley'}</span>
              </p>
            )}
          </div>
          
          {/* Main Progress Card */}
          <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-2xl border border-white/50 p-8 mb-8 animate-slide-up delay-100">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
              <div>
                <h2 className="text-3xl font-bold text-gray-800 mb-2">
                  Your Transfer Progress
                </h2>
                <p className="text-gray-600 text-lg">
                  Targeting <span className="font-bold text-indigo-600">{primaryAgreement?.major || navMajor}</span> at{' '}
                  <span className="font-bold text-purple-600">{primaryAgreement?.receiving_university || navUniversity}</span>
                </p>
              </div>
              <div className="text-center lg:text-right">
                <div className="text-6xl font-black bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  {courseProgress}%
            </div>
                <div className="text-gray-500 font-medium">
                  {completedCount} of {totalRequired} courses articulated
          </div>
                {totalGroups > 0 && (
                  <div className="text-sm text-gray-400 mt-1">
                    {satisfiedGroups}/{totalGroups} requirement groups complete
        </div>
                            )}
                          </div>
                        </div>
                        
                        {/* Progress Bar */}
            <div className="relative w-full bg-gray-200 rounded-full h-8 overflow-hidden">
              <div 
                className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-8 rounded-full animate-grow-width"
                style={{ width: `${courseProgress}%`, animationDelay: '0.5s' }}
              >
                <div className="absolute inset-0 animate-shimmer" style={{ animationDelay: '1.5s' }} />
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-sm font-bold text-white drop-shadow-md">
                  {completedCount}/{totalRequired} Courses Complete
                </span>
                          </div>
                        </div>
                        
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
              <div className="bg-gradient-to-br from-indigo-50 to-blue-100 rounded-2xl p-4 text-center border border-indigo-200 animate-pop-in" style={{ animationDelay: '0.3s' }}>
                <div className="text-3xl font-bold text-indigo-600">{gpaData.gpa}</div>
                <div className="text-sm text-indigo-700 font-medium">GPA</div>
                                </div>
              <div className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-2xl p-4 text-center border border-green-200 animate-pop-in" style={{ animationDelay: '0.4s' }}>
                <div className="text-3xl font-bold text-green-600">{studentCourses?.length || 0}</div>
                <div className="text-sm text-green-700 font-medium">Courses</div>
                            </div>
              <div className="bg-gradient-to-br from-blue-50 to-cyan-100 rounded-2xl p-4 text-center border border-blue-200 animate-pop-in" style={{ animationDelay: '0.5s' }}>
                <div className="text-3xl font-bold text-blue-600">{gpaData.totalUnits}</div>
                <div className="text-sm text-blue-700 font-medium">Total Units</div>
                          </div>
              <div className="bg-gradient-to-br from-emerald-50 to-teal-100 rounded-2xl p-4 text-center border border-emerald-200 animate-pop-in" style={{ animationDelay: '0.6s' }}>
                <div className="text-3xl font-bold text-emerald-600">{completedCount}</div>
                <div className="text-sm text-emerald-700 font-medium">Requirements Met</div>
                                </div>
              <div className="bg-gradient-to-br from-amber-50 to-orange-100 rounded-2xl p-4 text-center border border-amber-200 animate-pop-in" style={{ animationDelay: '0.7s' }}>
                <div className="text-3xl font-bold text-amber-600">{totalRequired - completedCount}</div>
                <div className="text-sm text-amber-700 font-medium">Still Needed</div>
                            </div>
                          </div>
                        </div>
                        
          {/* Completed & Remaining Requirements Side by Side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Completed Requirements */}
            <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-white/50 p-6 animate-slide-left delay-300">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="text-2xl">✅</span> Completed
                <span className="ml-auto bg-green-100 text-green-700 text-sm font-medium px-3 py-1 rounded-full">
                  {completedCount}
                </span>
              </h3>
              
              {comparison.completed_required && comparison.completed_required.length > 0 ? (
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
                  {comparison.completed_required.map((course, idx) => (
                    <div 
                      key={idx} 
                      className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-3 border border-green-200 flex justify-between items-center animate-slide-up"
                      style={{ animationDelay: `${0.4 + idx * 0.05}s` }}
                    >
                      <div>
                        <div className="font-bold text-green-800 text-sm">{course.course_code}</div>
                        <div className="text-xs text-gray-500">
                          ← {course.satisfied_by}
                        </div>
                                </div>
                      {course.student_grade && (
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          course.student_grade === 'A' ? 'bg-green-500 text-white' :
                          course.student_grade === 'B' ? 'bg-blue-500 text-white' :
                          course.student_grade === 'C' ? 'bg-yellow-500 text-white' :
                          course.student_grade === 'F' ? 'bg-red-500 text-white' :
                          'bg-gray-400 text-white'
                        }`}>
                          {course.student_grade}
                                  </span>
                              )}
                            </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-gray-400">
                  <p className="text-sm">No requirements completed yet</p>
                </div>
              )}
          </div>

            {/* Remaining Requirements */}
            <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-white/50 p-6 animate-slide-right delay-300">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="text-2xl">📋</span> Remaining
                <span className="ml-auto bg-amber-100 text-amber-700 text-sm font-medium px-3 py-1 rounded-full">
                  {comparison.missing_required?.length || 0}
                </span>
              </h3>
              
              {comparison.missing_required && comparison.missing_required.length > 0 ? (
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
                  {comparison.missing_required.map((course, idx) => (
                    <div 
                      key={idx} 
                      className={`rounded-lg p-3 border animate-slide-up ${
                        course.is_choice 
                          ? 'bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200' 
                          : 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200'
                      }`}
                      style={{ animationDelay: `${0.4 + idx * 0.05}s` }}
                    >
                      {course.is_choice ? (
                        <>
                          <div className="font-bold text-purple-800 text-sm flex items-center gap-1">
                            <span>🔀</span> {course.course_code}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            Choose from: <span className="text-purple-600">{course.course_name}</span>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="font-bold text-amber-800 text-sm">{course.course_code}</div>
                          {course.can_be_satisfied_by && (
                            <div className="text-xs text-gray-500 mt-1">
                              Take: <span className="text-purple-600 font-medium">{course.can_be_satisfied_by}</span>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-green-600">
                  <div className="text-3xl mb-1">🎉</div>
                  <p className="text-sm font-medium">All complete!</p>
              </div>
              )}
          </div>
        </div>

          {/* Requirement Groups Breakdown */}
          {Object.keys(groupResults).length > 0 && (
            <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-white/50 p-6 mb-8 animate-slide-up delay-500">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="text-2xl">📊</span> Requirement Groups
                <span className="ml-auto text-sm font-normal text-gray-500">
                  {satisfiedGroups}/{totalGroups} complete
                </span>
              </h3>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {Object.entries(groupResults).map(([groupId, group], idx) => {
                  const groupPct = group.required_count > 0 
                    ? Math.round((group.completed_count / group.required_count) * 100) 
                    : 100;
                  const isNFromArea = group.instruction_type === 'NFromArea';
                  
                  return (
                    <div
                      key={groupId}
                      className={`rounded-2xl p-4 border animate-pop-in ${
                        group.satisfied 
                          ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200' 
                          : 'bg-gradient-to-r from-slate-50 to-gray-50 border-gray-200'
                      }`}
                      style={{ animationDelay: `${0.6 + idx * 0.08}s` }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{group.satisfied ? '✅' : '⏳'}</span>
                          <div>
                            <div className="font-bold text-gray-800 text-sm">{group.title || 'Requirements'}</div>
                            <div className="text-xs text-gray-500">
                              {isNFromArea 
                                ? `Select ${group.required_count} from ${group.total_options}`
                                : `All ${group.required_count} required`
                              }
                            </div>
                          </div>
                        </div>
                        <div className={`text-xl font-bold ${group.satisfied ? 'text-green-600' : 'text-gray-600'}`}>
                          {group.completed_count}/{group.required_count}
                        </div>
                      </div>
                      
                      {/* Mini progress bar */}
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div 
                          className={`h-1.5 rounded-full transition-all ${
                            group.satisfied 
                              ? 'bg-gradient-to-r from-green-400 to-emerald-500' 
                              : 'bg-gradient-to-r from-indigo-400 to-purple-500'
                          }`}
                          style={{ width: `${Math.min(groupPct, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Your Courses with GPA */}
          {studentCourses && studentCourses.length > 0 && (
            <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-white/50 p-6 mb-8 animate-slide-up delay-600">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-4">
                <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                  <span className="text-2xl">📖</span> Your Transcript
                </h3>
                
                {/* GPA Display */}
                <div className="flex items-center gap-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl px-5 py-3 border border-indigo-200 animate-pop-in" style={{ animationDelay: '0.8s' }}>
                  <div className="text-center">
                    <div className="text-3xl font-black text-indigo-600">{gpaData.gpa}</div>
                    <div className="text-xs text-indigo-500 font-medium">GPA</div>
                  </div>
                  <div className="w-px h-10 bg-indigo-200"></div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-purple-600">{gpaData.totalUnits}</div>
                    <div className="text-xs text-purple-500 font-medium">Units</div>
                  </div>
                  <div className="w-px h-10 bg-indigo-200"></div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-gray-600">{studentCourses.length}</div>
                    <div className="text-xs text-gray-500 font-medium">Courses</div>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                {studentCourses.map((course, idx) => (
                  <div 
                    key={idx} 
                    className="bg-gradient-to-br from-slate-50 to-gray-100 rounded-lg p-2.5 border border-gray-200 hover:shadow-md hover:border-indigo-300 transition-all animate-pop-in"
                    style={{ animationDelay: `${0.7 + idx * 0.03}s` }}
                  >
                    <div className="font-bold text-gray-800 text-xs truncate">{course.course_code}</div>
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-xs text-gray-400">{course.credits}u</span>
                      {course.grade && (
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                          course.grade === 'A' ? 'bg-green-100 text-green-700' :
                          course.grade === 'B' ? 'bg-blue-100 text-blue-700' :
                          course.grade === 'C' ? 'bg-yellow-100 text-yellow-700' :
                          course.grade === 'F' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {course.grade}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transcript and What's Next Side by Side */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Agreement Selector (if multiple) - spans 2 cols */}
            {agreements && agreements.length > 1 && (
              <div className="lg:col-span-2 bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-white/50 p-6 animate-slide-left delay-700">
                <h3 className="text-lg font-bold text-gray-800 mb-3">Other Agreements</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {agreements.map((agreement, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedAgreementIdx(idx)}
                      className={`text-left p-3 rounded-lg border transition-all animate-slide-up ${
                        selectedAgreementIdx === idx 
                          ? 'border-indigo-500 bg-indigo-50' 
                          : 'border-gray-200 bg-white hover:border-indigo-300'
                      }`}
                      style={{ animationDelay: `${0.8 + idx * 0.05}s` }}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-bold text-gray-800 text-sm">{agreement.major}</div>
                          <div className="text-xs text-gray-500">{agreement.sending_name}</div>
                        </div>
                        <div className="text-lg font-bold text-indigo-600">
                          {agreement.comparison?.course_progress_percentage || 0}%
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* What's Next - Sidebar */}
            <div className={`${agreements && agreements.length > 1 ? 'lg:col-span-1' : 'lg:col-span-1'} bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-white/50 p-6 flex flex-col max-h-[500px] animate-slide-right delay-700`}>
              <div className="flex items-center justify-between mb-3 flex-shrink-0">
                <h3 className="text-lg font-bold text-gray-800">What's next?</h3>
                {!loadingRecs && recommendations && (
                  <button
                    onClick={() => { setRecommendations(''); fetchRecommendations(); }}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    ↻
                  </button>
                )}
              </div>
              
              <div className="overflow-y-auto flex-1">
                {loadingRecs ? (
                  <div className="flex items-center justify-center py-6">
                    <div className="w-6 h-6 border-2 border-gray-200 rounded-full animate-spin border-t-indigo-600"></div>
                    <span className="ml-2 text-sm text-gray-500">Loading...</span>
                  </div>
                ) : recsError ? (
                  <div className="text-center py-4">
                    <p className="text-sm text-gray-500 mb-2">{recsError}</p>
                    <button
                      onClick={fetchRecommendations}
                      className="text-sm text-indigo-600 hover:text-indigo-800"
                    >
                      Try again
                    </button>
                  </div>
                ) : recommendations ? (
                  <div className="text-base text-gray-700 space-y-4">
                    {recommendations.split('\n\n').map((section, idx) => {
                      if (section.startsWith('**')) {
                        const headerMatch = section.match(/^\*\*(.+?)\*\*/);
                        const header = headerMatch ? headerMatch[1] : '';
                        const content = section.replace(/^\*\*(.+?)\*\*\s*/, '');
                        
                        return (
                          <div key={idx}>
                            <div className="font-semibold text-gray-800 text-sm uppercase tracking-wide mb-1">{header}</div>
                            <div className="text-gray-600 leading-relaxed">
                              {content.split('\n').map((line, lineIdx) => {
                                if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
                                  return (
                                    <div key={lineIdx} className="flex items-start gap-2 mb-1">
                                      <span className="text-indigo-400 mt-0.5">•</span>
                                      <span className="text-sm">{parseMarkdown(line.replace(/^[-•]\s*/, ''))}</span>
                                    </div>
                                  );
                                }
                                if (line.trim()) {
                                  return <p key={lineIdx} className="text-sm mb-1">{parseMarkdown(line)}</p>;
                                }
                                return null;
                              })}
                            </div>
                          </div>
                        );
                      }
                      return section.trim() ? <p key={idx} className="text-sm text-gray-600">{parseMarkdown(section)}</p> : null;
                    })}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-sm text-gray-500 mb-3">Get personalized advice</p>
                    <button
                      onClick={fetchRecommendations}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                      Get tips
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => navigate('/')}
              className="px-8 py-4 rounded-2xl font-bold text-white bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-700 hover:via-purple-700 hover:to-pink-700 shadow-lg hover:shadow-xl transform hover:-translate-y-1 active:translate-y-0 transition-all duration-200 animate-bounce-in"
              style={{ animationDelay: '0.9s' }}
            >
              Analyze Another Transcript
            </button>
            {primaryAgreement?.agreement_data?.assist_url && (
              <a
                href={primaryAgreement.agreement_data.assist_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-8 py-4 rounded-2xl font-bold text-white bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg hover:shadow-xl transform hover:-translate-y-1 active:translate-y-0 transition-all duration-200 text-center flex items-center justify-center gap-2 animate-bounce-in"
                style={{ animationDelay: '1s' }}
              >
                <span>View Source on ASSIST.org</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}
            <button
              onClick={() => window.print()}
              className="px-8 py-4 rounded-2xl font-bold text-gray-700 bg-white border-2 border-gray-300 hover:border-indigo-400 hover:bg-gray-50 shadow-lg hover:shadow-xl transform hover:-translate-y-1 active:translate-y-0 transition-all duration-200 animate-bounce-in"
              style={{ animationDelay: '1.1s' }}
            >
              Print Results
          </button>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Results;
