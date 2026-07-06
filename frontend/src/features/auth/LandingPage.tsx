const features = [
  {
    icon: "view_kanban",
    title: "Kanban Boards",
    description:
      "Visualize workflows and move tasks effortlessly across stages.",
  },
  {
    icon: "person_add",
    title: "Smart Assignment",
    description:
      "Assign tasks to teammates and keep ownership perfectly clear.",
  },
  {
    icon: "forum",
    title: "Collaboration",
    description:
      "Comments, mentions, and activity tracking unified in one place.",
  },
  {
    icon: "notifications_active",
    title: "Notifications",
    description: "Stay updated with real-time task changes without the noise.",
  },
];

const tasks = [
  {
    status: "To Do",
    count: 3,
    priority: "High",
    title: "Design new landing page",
  },
  {
    status: "In Progress",
    count: 1,
    priority: "Medium",
    title: "Implement auth flow",
  },
  {
    status: "Done",
    count: 5,
    priority: "",
    title: "Review",
  },
];

import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

  const handleStart = () => {
    navigate("/signup");
  };

  const handleLogin = () => {
    navigate("/login");
  };

  const handleDemo = () => {
    console.log("Demo clicked");
  };

  return (
    <div className="min-h-screen bg-[#0b0e14] text-white font-sans">
      <header className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-cyan-400">ProSync</h1>

        <nav className="hidden md:flex gap-8 text-gray-400">
          {["Features", "Solutions", "Pricing", "About"].map((item) => (
            <span key={item} className="cursor-pointer hover:text-white">
              {item}
            </span>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <button
            onClick={handleLogin}
            className="text-gray-300 hover:text-white"
          >
            Login
          </button>

          <button
            onClick={handleStart}
            className="bg-cyan-500 text-black px-5 py-2 rounded-xl font-semibold"
          >
            Get Started
          </button>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-8 py-20 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <h2 className="text-5xl md:text-6xl font-bold leading-tight">
            Manage projects.
            <br />
            Track tasks.
            <br />
            Ship faster.
          </h2>

          <p className="mt-6 text-gray-400 text-lg">
            A powerful Kanban workspace for teams to organize tasks,
            collaborate, and deliver projects efficiently.
          </p>

          <div className="flex gap-4 mt-8">
            <button
              onClick={handleStart}
              className="bg-cyan-500 text-black px-6 py-3 rounded-xl font-semibold"
            >
              Start Building Free
            </button>

            <button
              onClick={handleDemo}
              className="border border-white/20 px-6 py-3 rounded-xl flex items-center gap-2"
            >
              <span className="material-symbols-outlined">play_circle</span>
              View Demo
            </button>
          </div>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6 space-y-4">
          {tasks.map((task) => (
            <div key={task.status} className="bg-white/5 rounded-2xl p-5">
              <div className="flex justify-between">
                <span>{task.status}</span>

                <span className="text-cyan-400">{task.count}</span>
              </div>

              <div className="mt-4">
                <p className="font-semibold">{task.title}</p>

                {task.priority && (
                  <span className="text-xs text-orange-400">
                    {task.priority}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="border-y border-white/10 py-8 text-center text-gray-400">
        Trusted by modern teams
        <div className="flex justify-center flex-wrap gap-8 mt-5">
          {["Acme Corp", "Globex", "Soylent", "Initech", "Umbrella"].map(
            (company) => (
              <span key={company}>{company}</span>
            ),
          )}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-8 py-20">
        <h2 className="text-4xl font-bold mb-12">
          Everything you need to ship.
        </h2>

        <div className="grid md:grid-cols-4 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="bg-white/5 border border-white/10 rounded-2xl p-6"
            >
              <span className="material-symbols-outlined text-cyan-400 text-3xl">
                {feature.icon}
              </span>

              <h3 className="text-xl font-bold mt-5">{feature.title}</h3>

              <p className="text-gray-400 mt-3">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-white/10 py-8 text-center text-gray-500">
        ProSync © 2024 ProSync. All rights reserved.
      </footer>
    </div>
  );
}
