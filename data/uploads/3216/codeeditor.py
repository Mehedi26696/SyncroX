# codeeditor.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import threading
import time

class ModernStyle:
    BG_COLOR = "#1e1e1e"
    SIDEBAR_BG = "#2d2d2d"
    CHAT_BG = "#3c3c3c"
    ENTRY_BG = "#4a4a4a"
    BUTTON_BG = "#007acc"
    ACCENT_COLOR = "#007acc"
    SUCCESS_COLOR = "#28a745"
    WARNING_COLOR = "#ffc107"
    DANGER_COLOR = "#dc3545"
    TEXT_COLOR = "#ffffff"
    SECONDARY_TEXT = "#cccccc"
    EDITOR_BG = "#2d2d2d"
    EDITOR_FG = "#ffffff"

class CodeEditorWindow:
    """Collaborative code editor window"""
    
    def __init__(self, parent, client, session_id=None, language="python"):
        self.parent = parent
        self.client = client
        self.session_id = session_id
        self.language = language
        self.participants = []
        self.last_code = ""
        self.update_lock = threading.Lock()
        
        self.create_window()
        
        # If no session_id, create a new session
        if not session_id:
            self.client.send_to_server(f"CREATE_CODE_SESSION|{language}")
    
    def create_window(self):
        """Create the code editor window"""
        self.window = tk.Toplevel(self.parent.root)
        self.window.title(f"Code Editor - {self.language.title()}")
        self.window.geometry("900x700")
        self.window.configure(bg=ModernStyle.BG_COLOR)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main editor area
        self.create_editor_area()
        
        # Create output area
        self.create_output_area()
        
        # Create bottom panel
        self.create_bottom_panel()
        
        # Start update checker
        self.start_update_checker()
    
    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = tk.Frame(self.window, bg=ModernStyle.SIDEBAR_BG, height=50)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        
        # Language label
        tk.Label(toolbar, text=f"Language: {self.language.title()}",
                font=("Arial", 12, "bold"),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.SIDEBAR_BG).pack(side="left", padx=10, pady=10)
        
        # Session ID label
        self.session_label = tk.Label(toolbar, text="Session: Creating...",
                                    font=("Arial", 10),
                                    fg=ModernStyle.SECONDARY_TEXT,
                                    bg=ModernStyle.SIDEBAR_BG)
        self.session_label.pack(side="left", padx=10)
        
        # Buttons frame
        buttons_frame = tk.Frame(toolbar, bg=ModernStyle.SIDEBAR_BG)
        buttons_frame.pack(side="right", padx=10, pady=5)
        
        # Run button
        self.run_btn = tk.Button(buttons_frame, text="▶ Run",
                               font=("Arial", 10, "bold"),
                               bg=ModernStyle.SUCCESS_COLOR,
                               fg=ModernStyle.TEXT_COLOR,
                               relief="flat", bd=0, padx=15, pady=5,
                               cursor="hand2",
                               command=self.run_code)
        self.run_btn.pack(side="right", padx=2)
        
        # Invite button
        self.invite_btn = tk.Button(buttons_frame, text="👥 Invite",
                                  font=("Arial", 10),
                                  bg=ModernStyle.BUTTON_BG,
                                  fg=ModernStyle.TEXT_COLOR,
                                  relief="flat", bd=0, padx=15, pady=5,
                                  cursor="hand2",
                                  command=self.invite_user)
        self.invite_btn.pack(side="right", padx=2)
        
        # Save button
        self.save_btn = tk.Button(buttons_frame, text="💾 Save",
                                font=("Arial", 10),
                                bg=ModernStyle.WARNING_COLOR,
                                fg=ModernStyle.TEXT_COLOR,
                                relief="flat", bd=0, padx=15, pady=5,
                                cursor="hand2",
                                command=self.save_code)
        self.save_btn.pack(side="right", padx=2)
    
    def create_editor_area(self):
        """Create the code editor area"""
        editor_frame = tk.Frame(self.window, bg=ModernStyle.BG_COLOR)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Editor with scrollbars
        text_frame = tk.Frame(editor_frame, bg=ModernStyle.BG_COLOR)
        text_frame.pack(fill="both", expand=True)
        
        # Line numbers frame
        line_frame = tk.Frame(text_frame, bg=ModernStyle.EDITOR_BG, width=50)
        line_frame.pack(side="left", fill="y")
        line_frame.pack_propagate(False)
        
        self.line_numbers = tk.Text(line_frame,
                                  bg=ModernStyle.EDITOR_BG,
                                  fg=ModernStyle.SECONDARY_TEXT,
                                  font=("Consolas", 11),
                                  relief="flat", bd=0,
                                  width=4,
                                  state="disabled",
                                  wrap="none")
        self.line_numbers.pack(fill="both", expand=True)
        
        # Code editor
        self.code_editor = tk.Text(text_frame,
                                 bg=ModernStyle.EDITOR_BG,
                                 fg=ModernStyle.EDITOR_FG,
                                 font=("Consolas", 11),
                                 relief="flat", bd=0,
                                 wrap="none",
                                 insertbackground=ModernStyle.TEXT_COLOR,
                                 selectbackground=ModernStyle.ACCENT_COLOR,
                                 undo=True, maxundo=50)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        h_scrollbar = tk.Scrollbar(editor_frame, orient="horizontal")
        
        self.code_editor.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        v_scrollbar.config(command=self.on_v_scroll)
        h_scrollbar.config(command=self.code_editor.xview)
        
        # Pack scrollbars and editor
        self.code_editor.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(fill="x")
        
        # Bind events
        self.code_editor.bind('<KeyRelease>', self.on_code_change)
        self.code_editor.bind('<ButtonRelease>', self.on_code_change)
        self.code_editor.bind('<FocusOut>', self.on_code_change)
        
        # Initial code
        initial_code = f"# Welcome to collaborative {self.language} coding!\n# Start writing your code here...\n\n"
        self.code_editor.insert("1.0", initial_code)
        self.last_code = initial_code
        self.update_line_numbers()
    
    def on_v_scroll(self, *args):
        """Handle vertical scrolling for both editor and line numbers"""
        self.code_editor.yview(*args)
        self.line_numbers.yview(*args)
    
    def create_output_area(self):
        """Create the output area"""
        output_frame = tk.LabelFrame(self.window, text="Output",
                                   bg=ModernStyle.BG_COLOR,
                                   fg=ModernStyle.TEXT_COLOR,
                                   font=("Arial", 10, "bold"))
        output_frame.pack(fill="x", padx=10, pady=5)
        
        # Output text widget
        output_text_frame = tk.Frame(output_frame, bg=ModernStyle.BG_COLOR)
        output_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.output_text = tk.Text(output_text_frame,
                                 bg=ModernStyle.CHAT_BG,
                                 fg=ModernStyle.TEXT_COLOR,
                                 font=("Consolas", 10),
                                 relief="flat", bd=0,
                                 height=8,
                                 state="disabled",
                                 wrap="word")
        
        output_scrollbar = tk.Scrollbar(output_text_frame, orient="vertical")
        self.output_text.config(yscrollcommand=output_scrollbar.set)
        output_scrollbar.config(command=self.output_text.yview)
        
        self.output_text.pack(side="left", fill="both", expand=True)
        output_scrollbar.pack(side="right", fill="y")
        
        # Configure output tags
        self.output_text.tag_config("success", foreground=ModernStyle.SUCCESS_COLOR)
        self.output_text.tag_config("error", foreground=ModernStyle.DANGER_COLOR)
        self.output_text.tag_config("info", foreground=ModernStyle.SECONDARY_TEXT)
    
    def create_bottom_panel(self):
        """Create the bottom panel with participants"""
        bottom_frame = tk.Frame(self.window, bg=ModernStyle.SIDEBAR_BG, height=40)
        bottom_frame.pack(fill="x")
        bottom_frame.pack_propagate(False)
        
        # Participants label
        tk.Label(bottom_frame, text="Participants:",
                font=("Arial", 10, "bold"),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.SIDEBAR_BG).pack(side="left", padx=10, pady=10)
        
        self.participants_label = tk.Label(bottom_frame, text="Loading...",
                                         font=("Arial", 10),
                                         fg=ModernStyle.SECONDARY_TEXT,
                                         bg=ModernStyle.SIDEBAR_BG)
        self.participants_label.pack(side="left", padx=5, pady=10)
    
    def update_line_numbers(self):
        """Update line numbers display"""
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        
        # Count lines in code editor
        lines = int(self.code_editor.index(tk.END).split('.')[0]) - 1
        line_numbers_text = "\n".join(str(i) for i in range(1, lines + 1))
        
        self.line_numbers.insert("1.0", line_numbers_text)
        self.line_numbers.config(state="disabled")
    
    def on_code_change(self, event=None):
        """Handle code changes"""
        current_code = self.code_editor.get("1.0", tk.END)
        
        # Update line numbers
        self.update_line_numbers()
        
        # Send update if code changed
        if current_code != self.last_code and self.session_id:
            with self.update_lock:
                self.last_code = current_code
                
                # Get cursor position
                cursor_pos = self.code_editor.index(tk.INSERT)
                
                update_data = {
                    'session_id': self.session_id,
                    'code': current_code,
                    'cursor_pos': cursor_pos
                }
                
                self.client.send_to_server(f"CODE_UPDATE|{json.dumps(update_data)}")
    
    def start_update_checker(self):
        """Start a thread to check for updates"""
        def update_checker():
            while hasattr(self, 'window') and self.window.winfo_exists():
                time.sleep(0.1)  # Check every 100ms
        
        update_thread = threading.Thread(target=update_checker)
        update_thread.daemon = True
        update_thread.start()
    
    def update_code(self, new_code, sender=None):
        """Update code from remote source"""
        if sender == self.client.username:
            return  # Don't update from own changes
        
        with self.update_lock:
            current_pos = self.code_editor.index(tk.INSERT)
            
            self.code_editor.delete("1.0", tk.END)
            self.code_editor.insert("1.0", new_code)
            
            # Try to restore cursor position
            try:
                self.code_editor.mark_set(tk.INSERT, current_pos)
            except:
                pass
            
            self.last_code = new_code
            self.update_line_numbers()
    
    def update_participants(self, participants):
        """Update participants list"""
        self.participants = participants
        participants_text = ", ".join(participants) if participants else "None"
        self.participants_label.config(text=participants_text)
    
    def run_code(self):
        """Execute the current code"""
        if not self.session_id:
            messagebox.showerror("Error", "No active session")
            return
        
        code = self.code_editor.get("1.0", tk.END)
        
        # Get input if needed
        input_data = ""
        if "input(" in code or "scanf" in code or "cin >>" in code:
            input_data = simpledialog.askstring("Input", "Enter input data (separate lines with \\n):")
            if input_data:
                input_data = input_data.replace("\\n", "\n")
        
        exec_data = {
            'session_id': self.session_id,
            'code': code,
            'language': self.language,
            'input': input_data or ""
        }
        
        self.client.send_to_server(f"EXECUTE_CODE|{json.dumps(exec_data)}")
        
        # Show "Running..." in output
        self.add_output("Running code...\n", "info")
    
    def handle_execution_result(self, result, executed_by):
        """Handle code execution result"""
        self.add_output(f"\n--- Execution by {executed_by} ---\n", "info")
        
        if result.get('success'):
            self.add_output("✅ Execution successful\n", "success")
            if result.get('output'):
                self.add_output("Output:\n", "info")
                self.add_output(result['output'], "success")
        else:
            self.add_output("❌ Execution failed\n", "error")
            if result.get('error'):
                self.add_output("Error:\n", "info")
                self.add_output(result['error'], "error")
        
        execution_time = result.get('execution_time', 0)
        self.add_output(f"\nExecution time: {execution_time:.2f}s\n", "info")
        self.add_output("-" * 40 + "\n", "info")
    
    def add_output(self, text, tag=""):
        """Add text to output area"""
        self.output_text.config(state="normal")
        self.output_text.insert(tk.END, text, tag)
        self.output_text.config(state="disabled")
        self.output_text.see(tk.END)
    
    def invite_user(self):
        """Invite a user to the session"""
        if not self.session_id:
            messagebox.showerror("Error", "No active session")
            return
        
        # Get list of available users
        available_users = [u for u in self.client.users_list if u != self.client.username and u not in self.participants]
        
        if not available_users:
            messagebox.showinfo("Info", "No users available to invite")
            return
        
        recipient = simpledialog.askstring("Invite User", 
                                         f"Enter username to invite:\nAvailable: {', '.join(available_users)}")
        
        if recipient and recipient in available_users:
            invite_data = {
                'recipient': recipient,
                'session_id': self.session_id
            }
            
            self.client.send_to_server(f"INVITE_TO_CODE|{json.dumps(invite_data)}")
            messagebox.showinfo("Success", f"Invitation sent to {recipient}")
        elif recipient:
            messagebox.showerror("Error", f"User '{recipient}' not available")
    
    def save_code(self):
        """Save the current code to a file"""
        from tkinter import filedialog
        
        code = self.code_editor.get("1.0", tk.END)
        
        # File extension based on language
        extensions = {
            'python': '.py',
            'javascript': '.js',
            'java': '.java',
            'cpp': '.cpp',
            'c': '.c'
        }
        
        default_ext = extensions.get(self.language, '.txt')
        
        file_path = filedialog.asksaveasfilename(
            title="Save Code",
            defaultextension=default_ext,
            filetypes=[(f"{self.language.title()} files", f"*{default_ext}"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                messagebox.showinfo("Success", f"Code saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

# Test the code editor
if __name__ == "__main__":
    class MockClient:
        def __init__(self):
            self.username = "test_user"
            self.users_list = ["user1", "user2", "user3"]
        
        def send_to_server(self, message):
            print(f"Sending: {message}")
    
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    client = MockClient()
    editor = CodeEditorWindow(None, client, "test123", "python")
    
    root.mainloop()