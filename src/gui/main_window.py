"""
Main GUI Window for Bigraph Cryptography System
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

# Add parent directory to path to import bigraph module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder


class BigramCryptoGUI:
    """Main GUI application for Bigraph Cryptography"""

    def __init__(self, root):
        """
        Initialize the GUI

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Bigraph Cryptography System")
        self.root.geometry("900x700")

        # Initialize key manager
        self.key_manager = KeyManager()
        self.current_key = None

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self.create_encode_tab()
        self.create_decode_tab()
        self.create_key_management_tab()
        self.create_symbol_viewer_tab()

        # Status bar
        self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_encode_tab(self):
        """Create the encode message tab"""
        encode_frame = ttk.Frame(self.notebook)
        self.notebook.add(encode_frame, text="Encode Message")

        # Key selection
        key_frame = ttk.LabelFrame(encode_frame, text="Encryption Key", padding=10)
        key_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(key_frame, text="Select Key:").grid(row=0, column=0, sticky='w')
        self.encode_key_var = tk.StringVar()
        self.encode_key_combo = ttk.Combobox(key_frame, textvariable=self.encode_key_var, state='readonly', width=40)
        self.encode_key_combo.grid(row=0, column=1, padx=5)

        ttk.Button(key_frame, text="Refresh Keys", command=self.refresh_encode_keys).grid(row=0, column=2, padx=5)
        ttk.Button(key_frame, text="Load Key", command=self.load_encode_key).grid(row=0, column=3, padx=5)

        # Input text
        input_frame = ttk.LabelFrame(encode_frame, text="Message to Encode", padding=10)
        input_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.encode_input = tk.Text(input_frame, height=10, wrap=tk.WORD)
        self.encode_input.pack(fill='both', expand=True)

        # Encode button
        ttk.Button(encode_frame, text="Encode Message", command=self.encode_message).pack(pady=10)

        # Output
        output_frame = ttk.LabelFrame(encode_frame, text="Encoded Output (Number List)", padding=10)
        output_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.encode_output = tk.Text(output_frame, height=8, wrap=tk.WORD)
        self.encode_output.pack(fill='both', expand=True)

        # Buttons
        button_frame = ttk.Frame(encode_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Save Encoded Message", command=self.save_encoded_message).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Copy to Clipboard", command=self.copy_encoded_to_clipboard).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_encode).pack(side='left', padx=5)

        self.refresh_encode_keys()

    def create_decode_tab(self):
        """Create the decode message tab"""
        decode_frame = ttk.Frame(self.notebook)
        self.notebook.add(decode_frame, text="Decode Message")

        # Key selection
        key_frame = ttk.LabelFrame(decode_frame, text="Decryption Key", padding=10)
        key_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(key_frame, text="Select Key:").grid(row=0, column=0, sticky='w')
        self.decode_key_var = tk.StringVar()
        self.decode_key_combo = ttk.Combobox(key_frame, textvariable=self.decode_key_var, state='readonly', width=40)
        self.decode_key_combo.grid(row=0, column=1, padx=5)

        ttk.Button(key_frame, text="Refresh Keys", command=self.refresh_decode_keys).grid(row=0, column=2, padx=5)
        ttk.Button(key_frame, text="Load Key", command=self.load_decode_key).grid(row=0, column=3, padx=5)

        # Input
        input_frame = ttk.LabelFrame(decode_frame, text="Encoded Message (Number List)", padding=10)
        input_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.decode_input = tk.Text(input_frame, height=8, wrap=tk.WORD)
        self.decode_input.pack(fill='both', expand=True)

        # Load button
        button_frame1 = ttk.Frame(decode_frame)
        button_frame1.pack(fill='x', padx=10, pady=5)
        ttk.Button(button_frame1, text="Load Encoded File", command=self.load_encoded_file).pack(side='left', padx=5)

        # Decode button
        ttk.Button(decode_frame, text="Decode Message", command=self.decode_message).pack(pady=10)

        # Output
        output_frame = ttk.LabelFrame(decode_frame, text="Decoded Message", padding=10)
        output_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.decode_output = tk.Text(output_frame, height=10, wrap=tk.WORD)
        self.decode_output.pack(fill='both', expand=True)

        # Buttons
        button_frame2 = ttk.Frame(decode_frame)
        button_frame2.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame2, text="Copy to Clipboard", command=self.copy_decoded_to_clipboard).pack(side='left', padx=5)
        ttk.Button(button_frame2, text="Clear", command=self.clear_decode).pack(side='left', padx=5)

        self.refresh_decode_keys()

    def create_key_management_tab(self):
        """Create the key management tab"""
        key_frame = ttk.Frame(self.notebook)
        self.notebook.add(key_frame, text="Key Management")

        # Generate new key
        gen_frame = ttk.LabelFrame(key_frame, text="Generate New Key", padding=10)
        gen_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(gen_frame, text="Recipient Name:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.recipient_name = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.recipient_name, width=30).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(gen_frame, text="Seed (optional):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.key_seed = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.key_seed, width=30).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(gen_frame, text="Generate Key", command=self.generate_new_key).grid(row=2, column=0, columnspan=2, pady=10)

        # Key list
        list_frame = ttk.LabelFrame(key_frame, text="Available Keys", padding=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create treeview for keys
        columns = ('Recipient', 'Created', 'Filename')
        self.key_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        self.key_tree.heading('Recipient', text='Recipient')
        self.key_tree.heading('Created', text='Created')
        self.key_tree.heading('Filename', text='Filename')

        self.key_tree.column('Recipient', width=200)
        self.key_tree.column('Created', width=200)
        self.key_tree.column('Filename', width=300)

        self.key_tree.pack(fill='both', expand=True)

        # Buttons
        button_frame = ttk.Frame(key_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Refresh List", command=self.refresh_key_list).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Export Key", command=self.export_key).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Import Key", command=self.import_key).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete Key", command=self.delete_key).pack(side='left', padx=5)

        self.refresh_key_list()

    def create_symbol_viewer_tab(self):
        """Create the symbol viewer tab"""
        viewer_frame = ttk.Frame(self.notebook)
        self.notebook.add(viewer_frame, text="Symbol Viewer")

        # Key selection
        key_frame = ttk.LabelFrame(viewer_frame, text="Key Selection", padding=10)
        key_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(key_frame, text="Select Key:").grid(row=0, column=0, sticky='w')
        self.viewer_key_var = tk.StringVar()
        self.viewer_key_combo = ttk.Combobox(key_frame, textvariable=self.viewer_key_var, state='readonly', width=40)
        self.viewer_key_combo.grid(row=0, column=1, padx=5)

        ttk.Button(key_frame, text="Refresh Keys", command=self.refresh_viewer_keys).grid(row=0, column=2, padx=5)
        ttk.Button(key_frame, text="Load Key", command=self.load_viewer_key).grid(row=0, column=3, padx=5)

        # Symbol display
        display_frame = ttk.LabelFrame(viewer_frame, text="Symbols", padding=10)
        display_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create scrollable text area for symbols
        self.symbol_text = tk.Text(display_frame, wrap=tk.WORD, height=20)
        scrollbar = ttk.Scrollbar(display_frame, orient='vertical', command=self.symbol_text.yview)
        self.symbol_text.configure(yscrollcommand=scrollbar.set)

        self.symbol_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.refresh_viewer_keys()

    # Event handlers
    def refresh_encode_keys(self):
        """Refresh the encode key dropdown"""
        keys = self.key_manager.list_keys()
        key_names = [f"{k['recipient']} - {k['created'][:10]}" for k in keys]
        self.encode_key_combo['values'] = key_names
        self.encode_keys_list = keys

    def refresh_decode_keys(self):
        """Refresh the decode key dropdown"""
        keys = self.key_manager.list_keys()
        key_names = [f"{k['recipient']} - {k['created'][:10]}" for k in keys]
        self.decode_key_combo['values'] = key_names
        self.decode_keys_list = keys

    def refresh_viewer_keys(self):
        """Refresh the viewer key dropdown"""
        keys = self.key_manager.list_keys()
        key_names = [f"{k['recipient']} - {k['created'][:10]}" for k in keys]
        self.viewer_key_combo['values'] = key_names
        self.viewer_keys_list = keys

    def load_encode_key(self):
        """Load selected key for encoding"""
        idx = self.encode_key_combo.current()
        if idx >= 0 and idx < len(self.encode_keys_list):
            key_info = self.encode_keys_list[idx]
            self.current_encode_key = self.key_manager.load_key(key_info['filepath'])
            self.status_bar.config(text=f"Loaded key for {key_info['recipient']}")
        else:
            messagebox.showwarning("Warning", "Please select a key first")

    def load_decode_key(self):
        """Load selected key for decoding"""
        idx = self.decode_key_combo.current()
        if idx >= 0 and idx < len(self.decode_keys_list):
            key_info = self.decode_keys_list[idx]
            self.current_decode_key = self.key_manager.load_key(key_info['filepath'])
            self.status_bar.config(text=f"Loaded key for {key_info['recipient']}")
        else:
            messagebox.showwarning("Warning", "Please select a key first")

    def load_viewer_key(self):
        """Load selected key for viewing"""
        idx = self.viewer_key_combo.current()
        if idx >= 0 and idx < len(self.viewer_keys_list):
            key_info = self.viewer_keys_list[idx]
            key = self.key_manager.load_key(key_info['filepath'])
            self.display_symbols(key)
            self.status_bar.config(text=f"Loaded symbols for {key_info['recipient']}")
        else:
            messagebox.showwarning("Warning", "Please select a key first")

    def encode_message(self):
        """Encode the input message"""
        if not hasattr(self, 'current_encode_key'):
            messagebox.showerror("Error", "Please load an encryption key first")
            return

        plaintext = self.encode_input.get('1.0', tk.END).strip()
        if not plaintext:
            messagebox.showwarning("Warning", "Please enter a message to encode")
            return

        try:
            encoder = BigramEncoder(self.current_encode_key)
            encoded = encoder.encode(plaintext)

            # Display encoded message
            self.encode_output.delete('1.0', tk.END)
            self.encode_output.insert('1.0', ','.join(map(str, encoded)))

            self.status_bar.config(text=f"Encoded {len(plaintext)} characters to {len(encoded)} symbols")
        except Exception as e:
            messagebox.showerror("Error", f"Encoding failed: {str(e)}")

    def decode_message(self):
        """Decode the input message"""
        if not hasattr(self, 'current_decode_key'):
            messagebox.showerror("Error", "Please load a decryption key first")
            return

        encoded_text = self.decode_input.get('1.0', tk.END).strip()
        if not encoded_text:
            messagebox.showwarning("Warning", "Please enter an encoded message to decode")
            return

        try:
            # Parse number list
            encoded = [int(x.strip()) for x in encoded_text.split(',') if x.strip()]

            decoder = BigramDecoder(self.current_decode_key)
            decoded = decoder.decode(encoded)

            # Display decoded message
            self.decode_output.delete('1.0', tk.END)
            self.decode_output.insert('1.0', decoded)

            self.status_bar.config(text=f"Decoded {len(encoded)} symbols to {len(decoded)} characters")
        except Exception as e:
            messagebox.showerror("Error", f"Decoding failed: {str(e)}")

    def save_encoded_message(self):
        """Save encoded message to file"""
        encoded_text = self.encode_output.get('1.0', tk.END).strip()
        if not encoded_text:
            messagebox.showwarning("Warning", "No encoded message to save")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".enc",
            filetypes=[("Encoded files", "*.enc"), ("All files", "*.*")]
        )

        if filepath:
            with open(filepath, 'w') as f:
                f.write(encoded_text)
            self.status_bar.config(text=f"Saved to {filepath}")

    def load_encoded_file(self):
        """Load encoded message from file"""
        filepath = filedialog.askopenfilename(
            filetypes=[("Encoded files", "*.enc"), ("All files", "*.*")]
        )

        if filepath:
            with open(filepath, 'r') as f:
                content = f.read()
            self.decode_input.delete('1.0', tk.END)
            self.decode_input.insert('1.0', content)
            self.status_bar.config(text=f"Loaded from {filepath}")

    def copy_encoded_to_clipboard(self):
        """Copy encoded message to clipboard"""
        encoded_text = self.encode_output.get('1.0', tk.END).strip()
        if encoded_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(encoded_text)
            self.status_bar.config(text="Copied to clipboard")

    def copy_decoded_to_clipboard(self):
        """Copy decoded message to clipboard"""
        decoded_text = self.decode_output.get('1.0', tk.END).strip()
        if decoded_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(decoded_text)
            self.status_bar.config(text="Copied to clipboard")

    def clear_encode(self):
        """Clear encode tab"""
        self.encode_input.delete('1.0', tk.END)
        self.encode_output.delete('1.0', tk.END)

    def clear_decode(self):
        """Clear decode tab"""
        self.decode_input.delete('1.0', tk.END)
        self.decode_output.delete('1.0', tk.END)

    def generate_new_key(self):
        """Generate a new encryption key"""
        recipient = self.recipient_name.get().strip()
        if not recipient:
            messagebox.showwarning("Warning", "Please enter a recipient name")
            return

        seed_str = self.key_seed.get().strip()
        seed = int(seed_str) if seed_str else None

        try:
            key = self.key_manager.generate_key(recipient, seed)
            filepath = self.key_manager.save_key(key)

            messagebox.showinfo("Success", f"Key generated and saved to:\n{filepath}")
            self.refresh_key_list()
            self.refresh_encode_keys()
            self.refresh_decode_keys()
            self.refresh_viewer_keys()

            # Clear inputs
            self.recipient_name.set('')
            self.key_seed.set('')

            self.status_bar.config(text=f"Generated key for {recipient}")
        except Exception as e:
            messagebox.showerror("Error", f"Key generation failed: {str(e)}")

    def refresh_key_list(self):
        """Refresh the key list"""
        # Clear existing items
        for item in self.key_tree.get_children():
            self.key_tree.delete(item)

        # Load keys
        keys = self.key_manager.list_keys()

        for key in keys:
            self.key_tree.insert('', 'end', values=(
                key['recipient'],
                key['created'][:19],  # Remove microseconds
                key['filename']
            ))

    def export_key(self):
        """Export selected key"""
        selection = self.key_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a key to export")
            return

        item = self.key_tree.item(selection[0])
        filename = item['values'][2]

        source_path = os.path.join(self.key_manager.keys_directory, filename)

        dest_path = filedialog.asksaveasfilename(
            defaultextension=".key",
            filetypes=[("Key files", "*.key"), ("All files", "*.*")],
            initialfile=filename
        )

        if dest_path:
            key = self.key_manager.load_key(source_path)
            self.key_manager.export_key(key, dest_path)
            messagebox.showinfo("Success", f"Key exported to:\n{dest_path}")
            self.status_bar.config(text=f"Exported {filename}")

    def import_key(self):
        """Import a key file"""
        filepath = filedialog.askopenfilename(
            filetypes=[("Key files", "*.key"), ("All files", "*.*")]
        )

        if filepath:
            try:
                key = self.key_manager.import_key(filepath)
                new_path = self.key_manager.save_key(key)

                messagebox.showinfo("Success", f"Key imported successfully:\n{new_path}")
                self.refresh_key_list()
                self.refresh_encode_keys()
                self.refresh_decode_keys()
                self.refresh_viewer_keys()

                self.status_bar.config(text=f"Imported key for {key['recipient']}")
            except Exception as e:
                messagebox.showerror("Error", f"Import failed: {str(e)}")

    def delete_key(self):
        """Delete selected key"""
        selection = self.key_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a key to delete")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this key?"):
            item = self.key_tree.item(selection[0])
            filename = item['values'][2]
            filepath = os.path.join(self.key_manager.keys_directory, filename)

            try:
                os.remove(filepath)
                self.refresh_key_list()
                self.refresh_encode_keys()
                self.refresh_decode_keys()
                self.refresh_viewer_keys()
                self.status_bar.config(text=f"Deleted {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Delete failed: {str(e)}")

    def display_symbols(self, key):
        """Display symbols from a key"""
        self.symbol_text.delete('1.0', tk.END)

        # Display sample symbols with their meanings
        self.symbol_text.insert(tk.END, "Symbol Mappings\n")
        self.symbol_text.insert(tk.END, "=" * 50 + "\n\n")

        # Show some bigrams as examples
        for i, (idx, meaning) in enumerate(list(key['symbol_to_meaning'].items())[:50]):
            self.symbol_text.insert(tk.END, f"Symbol {idx}: {meaning}\n")

        self.symbol_text.insert(tk.END, "\n... and more\n")
        self.symbol_text.insert(tk.END, f"\nTotal symbols: {len(key['symbol_to_meaning'])}\n")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = BigramCryptoGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
