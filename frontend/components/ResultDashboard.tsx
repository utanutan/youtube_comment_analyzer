'use client';

import { Download, Loader2, RefreshCw } from 'lucide-react';
import apiClient, { JobStatus } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface ResultDashboardProps {
  jobStatus: JobStatus | null | undefined;
  isLoading: boolean;
  onReset: () => void;
}

const COLORS = {
  positive: '#10b981',
  neutral: '#6b7280',
  negative: '#ef4444',
};

export default function ResultDashboard({ jobStatus, isLoading, onReset }: ResultDashboardProps) {
  const handleExport = async () => {
    if (!jobStatus?.jobId) return;
    try {
      const blob = await apiClient.exportCSV(jobStatus.jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comments_${jobStatus.jobId}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(`Export failed: ${error.message}`);
    }
  };

  if (isLoading || !jobStatus) {
    return (
      <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
        <Loader2 className="w-16 h-16 animate-spin text-blue-600 mx-auto mb-4" />
        <p className="text-xl text-gray-700">Loading analysis...</p>
      </div>
    );
  }

  if (jobStatus.status === 'queued' || jobStatus.status === 'running') {
    const progress = jobStatus.progress;
    const percentage = progress?.total
      ? Math.round((progress.analyzed / progress.total) * 100)
      : 0;

    return (
      <div className="bg-white rounded-2xl shadow-xl p-12">
        <div className="text-center mb-8">
          <Loader2 className="w-16 h-16 animate-spin text-blue-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            {jobStatus.status === 'queued' ? 'In Queue...' : 'Analyzing...'}
          </h2>
          <p className="text-gray-600">Job ID: {jobStatus.jobId}</p>
        </div>

        {progress && (
          <div className="max-w-md mx-auto">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Fetched: {progress.fetched}</span>
              <span>Analyzed: {progress.analyzed}</span>
              <span>{percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  if (jobStatus.status === 'failed') {
    return (
      <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
        <div className="text-red-600 mb-4">
          <p className="text-xl font-bold">Analysis Failed</p>
          <p className="text-sm mt-2">{jobStatus.error?.message}</p>
        </div>
        <button
          onClick={onReset}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg"
        >
          Try Again
        </button>
      </div>
    );
  }

  const summary = jobStatus.result?.summary;
  const comments = jobStatus.result?.comments || [];

  if (!summary) {
    return null;
  }

  const sentimentData = [
    { name: 'Positive', value: summary.sentimentDist.positive, color: COLORS.positive },
    { name: 'Neutral', value: summary.sentimentDist.neutral, color: COLORS.neutral },
    { name: 'Negative', value: summary.sentimentDist.negative, color: COLORS.negative },
  ];

  const topTokensData = summary.topTokens.slice(0, 10).map(([token, count]) => ({
    token,
    count,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-xl p-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Analysis Complete</h2>
          <p className="text-gray-600">Total Comments: {summary.totalComments}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center gap-2"
          >
            <Download className="w-5 h-5" />
            Export CSV
          </button>
          <button
            onClick={onReset}
            className="bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-5 h-5" />
            New Analysis
          </button>
        </div>
      </div>

      {/* Sentiment Distribution */}
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Sentiment Distribution</h3>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col justify-center space-y-4">
            {sentimentData.map((item) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: item.color }} />
                  <span className="font-medium">{item.name}</span>
                </div>
                <span className="text-xl font-bold">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Keywords */}
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Top Keywords</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={topTokensData}>
            <XAxis dataKey="token" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Comments Table */}
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Comments ({comments.length})</h3>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left">Author</th>
                <th className="px-4 py-2 text-left">Comment</th>
                <th className="px-4 py-2 text-center">Sentiment</th>
                <th className="px-4 py-2 text-center">Likes</th>
              </tr>
            </thead>
            <tbody>
              {comments.slice(0, 100).map((comment, idx) => (
                <tr key={idx} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">{comment.authorDisplayName}</td>
                  <td className="px-4 py-2 max-w-md truncate">{comment.textClean}</td>
                  <td className="px-4 py-2 text-center">
                    <span
                      className="px-2 py-1 rounded text-xs font-semibold"
                      style={{
                        backgroundColor: COLORS[comment.sentimentLabel as keyof typeof COLORS] + '20',
                        color: COLORS[comment.sentimentLabel as keyof typeof COLORS],
                      }}
                    >
                      {comment.sentimentLabel}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">{comment.likeCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

