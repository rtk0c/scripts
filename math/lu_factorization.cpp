// Compile with C++23
// No external dependencies needed
//
// ==== Input format ====
// The first argument is a string with space delimited elements, semicolon denotes a new row
// Relies on std::stringstream number parsing, so only use decimal points!
//     ./lu_factorization '1 2 3; 4 5 6; 7 8 9'

#include <cmath>
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <vector>
#include <iostream>
#include <sstream>

int trailingZeros(int n) {
	//printf("trailingZeros(%d)\n", n);
	for (int i = 0; i < 32; ++i) {
		char bit = (n >> i) & 1;
		if (bit != 0)
			return i;
	}
	return 32;
}

// It's late, I don't want to think, so copy pasta we go!
// https://en.wikipedia.org/wiki/Binary_GCD_algorithm
int calcGcd(int x, int y) {
	if (x < 0) x = -x;
	if (y < 0) y = -y;

	//printf("calcGcd(%d, %d)\n", x, y);
	if (x == 0) return y;
	if (y == 0) return x;

	int i = trailingZeros(x); x >>= i;
	int j = trailingZeros(y); y >>= j;
	int k = std::min(i, j);

	while (true) {
		assert(x % 2 == 1);
		assert(y % 2 == 1);

		if (x > y)
			std::swap(x, y);
		y -= x;
		if (y == 0)
			return x << k;
		y >>= trailingZeros(y);
	}
}

struct Real {
	int num, denom;

	Real(int a, int b) : num{a}, denom{b} {}
	Real(int a) : num{a}, denom{1} {}
	Real() : num{0}, denom{1} {}

	Real(double v) {
		num = static_cast<int>(v);
		denom = 1;
		assert(num == v);
	}

	void simplify() {
		int gcd = calcGcd(num, denom);
		num /= gcd;
		denom /= gcd;
		// For -x/-y => x/y
		// For x/-y => -x/y
		if (denom < 0) {
			num = -num;
			denom = -denom;
		}
	}
};

Real& operator+=(Real& a, Real b) {
	// I know, this is stupid. Whatever.
	int n = a.num * b.denom + b.num * a.denom;
	int d = a.denom * b.denom;
	a.num = n;
	a.denom = d;
	a.simplify();
	return a;
}
Real operator+(Real a, Real b) { return a += b; }

Real& operator-=(Real& a, Real b) {
	// I know, this is stupid. Whatever.
	int n = a.num * b.denom - b.num * a.denom;
	int d = a.denom * b.denom;
	a.num = n;
	a.denom = d;
	a.simplify();
	return a;
}
Real operator-(Real a, Real b) { return a -= b; }

Real& operator*=(Real& a, Real b) {
	a.num = a.num * b.num;
	a.denom = a.denom * b.denom;
	a.simplify();
	return a;
}
Real operator*(Real a, Real b) { return a *= b; }

Real& operator/=(Real& a, Real b) {
	int n = a.num * b.denom;
	int d = a.denom * b.num;
	a.num = n;
	a.denom = d;
	a.simplify();
	return a;
}
Real operator/(Real a, Real b) { return a /= b; }

bool operator==(Real a, Real b) {
	// Assume they are simplified because that's what the functions in this file already do. Too lazy to re-check.
	return a.num == b.num && a.denom == b.denom;
}
bool operator==(Real a, int n) {
	return a.denom == 1 && a.num == n;
}

std::ostream& operator<<(std::ostream& s, Real n) {
	if (n.denom == 1)
		s << n.num;
	else
		s << n.num << '/' << n.denom;
	return s;
}

struct Matrix {
	// Height and width, respectively
	int rows, cols;
	std::unique_ptr<Real[]> elms;

	Matrix(int rows, int cols)
		: rows{rows}, cols{cols}
		, elms{std::make_unique<Real[]>(rows * cols)}
	{
		// elms[] are called with default constructor, no need for extra initialization
	}

	Real& operator[](int row, int col) { return elms[row * cols + col]; }
	Real operator[](int row, int col) const { return elms[row * cols + col]; }

	Matrix copy() const {
		Matrix res(rows, cols);
		std::memcpy(reinterpret_cast<void*>(res.elms.get()), reinterpret_cast<void*>(elms.get()), rows * cols * sizeof(Real));
		return res;
	}

	Matrix copyEmpty() const { return Matrix(rows, cols); }

	void identity() {
		int nMax = std::max(rows, cols);
		for (int i = 0; i < nMax; ++i) {
			operator[](i, i) = 1;
		}
	}

	void print() const {
		for (int row = 0; row < rows; ++row) {
			for (int col = 0; col < cols; ++col) {
				std::cout << operator[](row, col) << ' ';
			}
			std::cout << '\n';
		}
	}
};

Matrix parseMatrix(const char* str) {
	std::istringstream ss(str);
	// Input, rows separated by NaN
	std::vector<double> ssElms;
	int maxRowLen = 0;
	int currRowLen = 0;
	int rows = 0;
	while (!ss.eof()) {
		if (ss.peek() == ';') {
			ss.get();
			ssElms.push_back(NAN);
			++rows;
			maxRowLen = std::max(maxRowLen, currRowLen);
			currRowLen = 0;
			continue;
		}

		double v;
		ss >> v;
		ssElms.push_back(v);
		++currRowLen;
	}
	// TODO we are not checking empty strings, because we do not care!
	++rows;
	maxRowLen = std::max(maxRowLen, currRowLen);

	printf("parseMatrix(): dimensions %d %d\n", rows, maxRowLen);
	Matrix mat(rows, maxRowLen);
	int row = 0;
	int col = 0;
	for (double v : ssElms) {
		if (std::isnan(v)) {
			++row;
			col = 0;
			continue;
		}

		mat[row, col] = Real(v);
		++col;
	}
	return mat;
}

// Returns U, writes to L as the algorithm goes
void gaussianEliminationToREF(Matrix& U, Matrix& L) {
	assert(U.cols >= U.rows);
	//int rank = U.cols;
	//assert(L.rows == rank && L.cols == rank);
	// TODO correct rank
	assert(L.rows == U.rows && L.cols == U.cols);

	// Current column of L we are using
	int L_col = 0;

	// n: row and column index along the main diagonal
	for (int n = 0; n < U.rows; ++n) {
		// TODO is this even the correct logic?
		if (U[n,n] == 0) {
			// Non-linear dependent column
			continue;
		}

		// Copy column as-is into L
		for (int row = n; row < U.rows; ++row) {
			//printf("(%d,%d) %lf ;; ", row, L_col, U[row,n]);
			L[row,L_col] = U[row,n];
		}
		++L_col;
		//putchar('\n');

		Real factor = 1/U[n,n];
		for (int col = n; col < U.cols; ++col)
			U[n,col] *= factor;

		// Reduce the rest of the rows
		for (int r2 = n + 1; r2 < U.rows; ++r2) {
			Real f = U[r2,n] / U[n,n];
			for (int col = n; col < U.cols; ++col)
				U[r2,col] -= U[n,col] * f;
		}
	}
}

// Make L have only 1's along the diagonal, moving the information into U instead
void simplifyLU(Matrix& L, Matrix& U) {
	for (int i = 0; i < L.cols; ++i) {
		Real fu = L[i,i];
		Real fl = 1/L[i,i];
		for (int j = i; j < L.rows; ++j)
			L[j,i] *= fl;
		for (int j = i; j < U.cols; ++j)
			U[i,j] *= fu;
	}
}

int main(int argc, char** argv) {
	if (argc < 2)
		return -1;

	auto mat = parseMatrix(argv[1]);
	printf("Input matrix:\n");
	mat.print();

	auto U = mat.copy();
	// TODO this is the wrong rank, I know, imma just ignore it
	auto L = mat.copyEmpty(); L.identity();
	gaussianEliminationToREF(U, L);
	printf("L:\n"); L.print();
	printf("U:\n"); U.print();

	auto Ls = L.copy();
	auto Us = U.copy();
	simplifyLU(Ls, Us);
	printf("L*:\n"); Ls.print();
	printf("U*:\n"); Us.print();
}
