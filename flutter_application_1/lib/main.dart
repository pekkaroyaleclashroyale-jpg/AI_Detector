import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:percent_indicator/percent_indicator.dart';
import 'dart:convert';
import 'dart:io';
import 'dart:ui'; // Обязательно для эффектов размытия
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:typed_data';

void main() => runApp(const AIDetectorApp());

class AIDetectorApp extends StatelessWidget {
  const AIDetectorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4F46E5),
          background: const Color(0xFFF1F5F9),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  final String serverUrl = "http://192.168.0.13:8000"; 
  int _currentIndex = 0;
  
  File? _selectedImage;
  Uint8List? _webImage;
  final _textController = TextEditingController();
  
  String _verdict = "Ожидание анализа";
  double _aiProbability = 0.0;
  bool _isLoading = false;

  void _updateResult(String label, double probability) {
    setState(() {
      _verdict = label;
      _aiProbability = probability;
    });
  }

  // --- ЛОГИКА ---
  Future<void> checkText() async {
    if (_textController.text.trim().length < 10) return;
    setState(() => _isLoading = true);
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/detect-text'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"text": _textController.text}),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _updateResult(data['label'], (data['ai_score'] as num).toDouble());
      }
    } catch (e) { _showError(); } 
    finally { setState(() => _isLoading = false); }
  }

  Future<void> pickAndCheckImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.gallery);
    if (pickedFile != null) {
      if (kIsWeb) {
        final bytes = await pickedFile.readAsBytes();
        setState(() { _webImage = bytes; _isLoading = true; });
      } else {
        setState(() { _selectedImage = File(pickedFile.path); _isLoading = true; });
      }
      try {
        var request = http.MultipartRequest('POST', Uri.parse('$serverUrl/upload'));
        request.files.add(http.MultipartFile.fromBytes('file', await pickedFile.readAsBytes(), filename: pickedFile.name));
        var res = await http.Response.fromStream(await request.send());
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          double prob = (data['ai_probability'] as num).toDouble();
          if (prob <= 1.0) prob *= 100;
          _updateResult(prob > 50 ? "AI Generated" : "Human Content", prob);
        }
      } catch (e) { _showError(); }
      finally { setState(() => _isLoading = false); }
    }
  }

  void _showError() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: const Text("Ошибка сервера"), behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)))
    );
  }

  // --- UI КОМПОНЕНТЫ ---

  Widget _buildScannerPage() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("AIDetector.", style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: -1.2, color: Color(0xFF1E293B))),
          const Text("Умная проверка вашего контента", style: TextStyle(color: Color(0xFF64748B), fontSize: 15, fontWeight: FontWeight.w500)),
          const SizedBox(height: 32),
          
          // Поле ввода
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 24, offset: const Offset(0, 8))],
            ),
            child: TextField(
              controller: _textController,
              maxLines: 5,
              decoration: InputDecoration(
                hintText: "Вставьте текст для анализа...",
                hintStyle: TextStyle(color: Colors.grey.withOpacity(0.6)),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.all(24),
              ),
            ),
          ),
          const SizedBox(height: 20),
          
          // Анимированная кнопка
          AnimatedScale(
            scale: _isLoading ? 0.97 : 1.0,
            duration: const Duration(milliseconds: 100),
            child: SizedBox(
              width: double.infinity,
              height: 64,
              child: ElevatedButton(
                onPressed: _isLoading ? null : checkText,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4F46E5),
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
                child: _isLoading 
                  ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text("Проверить текст", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              ),
            ),
          ),

          const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Row(children: [Expanded(child: Divider(color: Color(0xFFE2E8F0))), Padding(padding: EdgeInsets.symmetric(horizontal: 16), child: Text("ИЛИ", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF94A3B8)))), Expanded(child: Divider(color: Color(0xFFE2E8F0)))]),
          ),

          // Загрузка фото
          // Замени блок GestureDetector для загрузки фото на этот код:
GestureDetector(
  onTap: _isLoading ? null : pickAndCheckImage,
  child: AnimatedContainer(
    duration: const Duration(milliseconds: 200),
    height: 160,
    width: double.infinity,
    clipBehavior: Clip.antiAlias, // Чтобы размытие не выходило за края
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: const Color(0xFFE2E8F0), width: 1.5),
      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10)],
    ),
    child: (_webImage != null || _selectedImage != null)
        ? Stack(
            fit: StackFit.expand,
            children: [
              // Сама картинка с эффектом размытия
              ImageFiltered(
                imageFilter: ColorFilter.mode(
                  Colors.black.withOpacity(0.1), // Немного притемняем для контраста
                  BlendMode.darken,
                ),
                child: ImageFiltered(
                  imageFilter: ImageFilter.blur(sigmaX: 8, sigmaY: 8), // Уровень размытия
                  child: kIsWeb 
                    ? Image.memory(_webImage!, fit: BoxFit.cover) 
                    : Image.file(_selectedImage!, fit: BoxFit.cover),
                ),
              ),
              // Поверх размытого фото можно вернуть иконку или текст
              const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.refresh_rounded, size: 32, color: Colors.white),
                    SizedBox(height: 8),
                    Text("Заменить фото", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, shadows: [Shadow(blurRadius: 10, color: Colors.black45)])),
                  ],
                ),
              ),
            ],
          )
        : const Column(
            mainAxisAlignment: MainAxisAlignment.center, 
            children: [
              Icon(Icons.add_a_photo_rounded, size: 32, color: Color(0xFF4F46E5)),
              SizedBox(height: 8),
              Text("Загрузить изображение", style: TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF4F46E5))),
            ],
          ),
  ),
),

          const SizedBox(height: 32),

          // Анимированная карточка результата
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 600),
            transitionBuilder: (child, animation) => FadeTransition(
              opacity: animation,
              child: SlideTransition(position: Tween<Offset>(begin: const Offset(0, 0.2), end: Offset.zero).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic)), child: child),
            ),
            child: (_aiProbability > 0 || _isLoading)
                ? Container(
                    key: ValueKey(_aiProbability),
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 40, offset: const Offset(0, 12))],
                    ),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(_verdict, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: _aiProbability > 50 ? Colors.redAccent : const Color(0xFF10B981))),
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(color: (_aiProbability > 50 ? Colors.redAccent : const Color(0xFF10B981)).withOpacity(0.1), shape: BoxShape.circle),
                              child: Icon(_aiProbability > 50 ? Icons.priority_high_rounded : Icons.done_rounded, size: 20, color: _aiProbability > 50 ? Colors.redAccent : const Color(0xFF10B981)),
                            )
                          ],
                        ),
                        const SizedBox(height: 24),
                        LinearPercentIndicator(
                          lineHeight: 14.0,
                          percent: _aiProbability / 100,
                          barRadius: const Radius.circular(7),
                          progressColor: _aiProbability > 50 ? Colors.redAccent : const Color(0xFF6366F1),
                          backgroundColor: const Color(0xFFF1F5F9),
                          animation: true,
                          animationDuration: 1000,
                          curve: Curves.easeOutExpo,
                          padding: EdgeInsets.zero,
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text("Уровень риска", style: TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w600, fontSize: 13)),
                            Text("${_aiProbability.toStringAsFixed(1)}%", style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Color(0xFF1E293B))),
                          ],
                        ),
                      ],
                    ),
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoPage() {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Text("Информация", style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900, letterSpacing: -0.5)),
        const SizedBox(height: 24),
        _buildInfoCard("Текстовый детектор", "Использует лингвистический анализ для поиска паттернов, характерных для моделей GPT-4 и Claude.", Icons.text_fields_rounded),
        _buildInfoCard("Визуальный детектор", "Анализирует шум изображения, артефакты генерации и несоответствия в геометрии.", Icons.remove_red_eye_rounded),
      ],
    );
  }

  Widget _buildInfoCard(String title, String body, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE2E8F0))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF4F46E5)),
          const SizedBox(width: 16),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)), const SizedBox(height: 4), Text(body, style: const TextStyle(color: Color(0xFF64748B), fontSize: 14))])),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F5F9),
      body: SafeArea(child: _currentIndex == 0 ? _buildScannerPage() : _buildInfoPage()),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        elevation: 0,
        backgroundColor: Colors.white,
        selectedItemColor: const Color(0xFF4F46E5),
        unselectedItemColor: const Color(0xFF94A3B8),
        showSelectedLabels: false,
        showUnselectedLabels: false,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.auto_awesome_mosaic_rounded), label: "Сканер"),
          BottomNavigationBarItem(icon: Icon(Icons.info_rounded), label: "Инфо"),
        ],
      ),
    );
  }
}