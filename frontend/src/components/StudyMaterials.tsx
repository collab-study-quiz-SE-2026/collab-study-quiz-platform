import { useState, useEffect, useRef, FormEvent, ChangeEvent } from "react";
import { StudyMaterial } from "../types";
import { listStudyMaterials, uploadStudyMaterial, downloadStudyMaterialFile } from "../api";

export default function StudyMaterials() {
  const [activeTab, setActiveTab] = useState<"browse" | "upload">("browse");
  const [materials, setMaterials] = useState<StudyMaterial[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [browseError, setBrowseError] = useState<string | null>(null);
  const hasFilters = Boolean(searchQuery || subjectFilter || topicFilter || tagFilter);
  const browseRequest = useRef(0);

  // Upload Form State
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [courseCode, setCourseCode] = useState("");
  const [subject, setSubject] = useState("Computer Science");
  const [topic, setTopic] = useState("Database Systems");
  const [tags, setTags] = useState("");
  const [uploading, setUploading] = useState(false);

  async function loadMaterials() {
    const request = ++browseRequest.current;
    setLoading(true);
    setBrowseError(null);
    try {
      const data = await listStudyMaterials({
        search: searchQuery || undefined,
        subject: subjectFilter || undefined,
        topic: topicFilter || undefined,
        tag: tagFilter || undefined,
      });
      if (request === browseRequest.current) setMaterials(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load study materials";
      if (request === browseRequest.current) setBrowseError(msg);
    } finally {
      if (request === browseRequest.current) setLoading(false);
    }
  }

  useEffect(() => {
    void loadMaterials();
  }, [searchQuery, subjectFilter, topicFilter, tagFilter]);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.size > 25 * 1024 * 1024) {
        alert("File size exceeds 25 MB limit");
        e.target.value = "";
        setFile(null);
        return;
      }
      setFile(selected);
      if (!title) {
        // Auto-fill title from filename
        setTitle(selected.name.replace(/\.[^/.]+$/, ""));
      }
    }
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setMessage({ text: "Please select a PDF or Markdown file", type: "error" });
      return;
    }

    setUploading(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title.trim());
      formData.append("course_code", courseCode.trim().toUpperCase());
      formData.append("subject", subject.trim());
      formData.append("topic", topic.trim());
      formData.append("tags", tags.trim());

      await uploadStudyMaterial(formData);
      setMessage({ text: `"${title}" uploaded to S3 storage successfully!`, type: "success" });

      // Reset
      setFile(null);
      setTitle("");
      setCourseCode("");
      setTags("");
      setActiveTab("browse");
      void loadMaterials();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload file";
      setMessage({ text: msg, type: "error" });
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(material: StudyMaterial) {
    try {
      await downloadStudyMaterialFile(material.id, material.original_filename);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Download failed";
      alert(msg);
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className="feature-container">
      <div className="section-header">
        <div>
          <h2>Shared Study Materials</h2>
          <p className="subtitle">Upload and download course notes stored in S3-compatible cloud storage</p>
        </div>
        <div className="tab-pill-group">
          <button
            type="button"
            className={activeTab === "browse" ? "pill-btn active" : "pill-btn"}
            onClick={() => setActiveTab("browse")}
          >
            Browse Materials ({materials.length})
          </button>
          <button
            type="button"
            className={activeTab === "upload" ? "pill-btn active" : "pill-btn"}
            onClick={() => setActiveTab("upload")}
          >
            + Upload Document
          </button>
        </div>
      </div>

      {message && (
        <div className={`banner-alert ${message.type === "success" ? "banner-success" : "banner-error"}`}>
          {message.text}
        </div>
      )}

      {/* ================= TAB 1: BROWSE ================= */}
      {activeTab === "browse" && (
        <div>
          <div className="search-filter-grid">
            <div className="search-box">
              <label htmlFor="mat-search">Search Materials</label>
              <input
                id="mat-search"
                type="text"
                placeholder="Search titles, course codes (e.g. CS301), tags…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="mat-sub">Subject Filter</label>
              <input
                id="mat-sub"
                type="text"
                placeholder="e.g. Computer Science"
                value={subjectFilter}
                onChange={(e) => setSubjectFilter(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="mat-top">Topic Filter</label>
              <input
                id="mat-top"
                type="text"
                placeholder="e.g. Database Systems"
                value={topicFilter}
                onChange={(e) => setTopicFilter(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label htmlFor="mat-tag">Tag Filter</label>
            <input id="mat-tag" type="text" placeholder="e.g. exam-prep"
              value={tagFilter} onChange={(e) => setTagFilter(e.target.value)} />
            <p className="form-subtext">Subject and topic must match the full value and letter case. Tags match full values, ignoring letter case. Search accepts part of a title, course code or tag.</p>
            {hasFilters && (
              <button type="button" className="secondary" onClick={() => {
                setSearchQuery(""); setSubjectFilter(""); setTopicFilter(""); setTagFilter("");
              }}>Clear filters</button>
            )}
          </div>

          {loading ? (
            <p className="loading-state">Loading study materials…</p>
          ) : browseError ? (
            <div className="banner-alert banner-error" role="alert">
              <p>{browseError}</p>
              <button type="button" onClick={() => void loadMaterials()}>Retry</button>
            </div>
          ) : materials.length === 0 ? (
            <div className="empty-state">
              <p>{hasFilters ? "No materials match these filters. Try different values or clear the filters." : "No study materials have been uploaded yet."}</p>
              {!hasFilters && <button type="button" onClick={() => setActiveTab("upload")}>Upload the first document</button>}
            </div>
          ) : (
            <div className="cards-grid">
              {materials.map((m) => (
                <div key={m.id} className="item-card material-card">
                  <div className="card-top">
                    <span className="course-code-badge">{m.course_code}</span>
                    <span className="badge badge-subject">{m.subject}</span>
                    <span className="file-size-tag">{formatBytes(m.file_size)}</span>
                  </div>
                  <h4>{m.title}</h4>
                  <p className="material-meta">
                    <strong>Topic:</strong> {m.topic} • <strong>File:</strong> {m.original_filename}
                  </p>
                  {m.tags && m.tags.length > 0 && (
                    <div className="tags-container">
                      {m.tags.map((t, idx) => (
                        <span key={idx} className="tag-pill">#{t}</span>
                      ))}
                    </div>
                  )}
                  <div className="card-bottom">
                    <button
                      type="button"
                      className="download-btn"
                      onClick={() => handleDownload(m)}
                    >
                      📥 Download File
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 2: UPLOAD ================= */}
      {activeTab === "upload" && (
        <form onSubmit={handleUpload} className="styled-form">
          <h3>Upload Study Document</h3>
          <p className="form-subtext">PDF and Markdown files up to 25 MB are stored in S3 persistent object storage.</p>

          <label htmlFor="file-input">Select File (PDF or Markdown) *</label>
          <input
            id="file-input"
            type="file"
            accept=".pdf,.md,.markdown,text/markdown,application/pdf"
            onChange={handleFileChange}
            required
          />

          <label htmlFor="doc-title">Document Title *</label>
          <input
            id="doc-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Relational Calculus & Normalization Lecture Notes"
            required
          />

          <div className="form-row-3">
            <div>
              <label htmlFor="doc-course">Course Code *</label>
              <input
                id="doc-course"
                type="text"
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
                placeholder="e.g. CS301"
                required
              />
            </div>
            <div>
              <label htmlFor="doc-sub">Subject *</label>
              <input
                id="doc-sub"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="doc-top">Topic *</label>
              <input
                id="doc-top"
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </div>
          </div>

          <label htmlFor="doc-tags">Tags (Comma-separated)</label>
          <input
            id="doc-tags"
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="e.g. bcnf, 3nf, exam-prep, midterm"
          />

          <button type="submit" disabled={uploading}>
            {uploading ? "Uploading to S3…" : "Upload Material to S3 Storage"}
          </button>
        </form>
      )}
    </div>
  );
}
