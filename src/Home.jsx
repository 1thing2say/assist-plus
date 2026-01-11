import DocumentAnalyzer from './DocumentAnalyzer'

function Home() {
    return (
        <div className="container mx-auto px-6 py-16">
            <div className="max-w-4xl mx-auto text-center mb-16">
                <h1 className="text-5xl font-bold text-gray-800 mb-6 animate-slide-up">
                    Welcome to <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent font-bold">assist+</span>
                </h1>
                <p className="text-xl text-gray-600 mb-8 leading-relaxed animate-slide-up delay-100">
                    Upload your transcript and get instant feedback and recommendations.
                </p>

            </div>
            
            {/* Document Analyzer Section */}
            <div className="flex justify-center items-start animate-slide-up delay-200">
                <div className="w-full max-w-4xl">
                    <DocumentAnalyzer expandedView={true} />
                </div>
            </div>
        </div>
    );
}

export default Home