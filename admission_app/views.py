from multiprocessing import context
from django.http import HttpResponse
from django.shortcuts import render, redirect
from admission_app.models import *
from django.contrib import messages
import bcrypt
import os 


def index(request):
  u = User.objects.get(id=1)
  u.role = 'admin'
  u.save()
  return redirect('/home')

def register(request):
    #if the user is logged in, redirect to home page, dont show register and login page
    if 'userId' in request.session:
        return redirect('/home')
    if request.method == "POST":
        errors = User.objects.basic_validator(request.POST)
        if len(errors) > 0:
            for key, errorMessage in errors.items():
                messages.error(request, errorMessage)
            return redirect("/register")
        else:
            first_name = request.POST["first_name"]
            last_name = request.POST["last_name"]
            email = request.POST["email"]
            phone= request.POST["phone"]
            password = request.POST["password"]
            passwordHash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            newUser = User.objects.create(first_name=first_name,last_name=last_name,email=email,phone=phone,role = "Student", password=passwordHash)
            request.session["userId"] = newUser.id
            request.session['role'] = newUser.role
            return redirect("/home")
    return render(request,"index.html")

def login(request):
    if request.method == "POST":
        if (User.objects.filter(email=request.POST['email']).exists()):
            user = User.objects.get(email=request.POST['email'])
            if (bcrypt.checkpw(request.POST['password'].encode(), user.password.encode())):
                request.session['userId'] = user.id
                request.session['role'] = user.role
                if(user.role=="admin"):
                    return redirect("/admin")
                else:   
                    return redirect("/home")
            else:
                messages.error(request, "User password do not match")
        else:
            messages.error(request, "User not found")
    return redirect('/register')

def home(request):
    if "userId" in request.session:
        user = User.objects.get(id=request.session["userId"])

    msg=Message.objects.filter(read=False)
    request.session["msgs"]=len(msg)
    course=Course.objects.all()
    context = {
            "courses":course,
            'count_course':len(course)-1,
        }
    return render(request, 'home.html', context)

def admin(request):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")

    user = User.objects.get(id=request.session["userId"])
    courses =Course.objects.all()
    students = User.objects.filter(state="pending")
    request.session["request_pending"]=len(students)
    
    if(user.role=="admin"):
        context = {
            "user": user,
            "courses":courses,
            "students":students,
        }
        return render(request, 'admin.html', context)
    return HttpResponse("Please authenticate first")

def add_course(request):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")
    if request.method == "POST":
        errors = Course.objects.basic_validator_files(request.FILES)
        errors.update(Course.objects.basic_validator(request.POST))
        if len(errors) > 0:
            for key, errorMessage in errors.items():
                messages.error(request, errorMessage)
            return redirect("/add_course")
        else:
            name = request.POST["name"]
            desc = request.POST["desc"]
            capacity=request.POST["capacity"]
            photo = request.FILES['photo']
            course = Course.objects.create(name=name,desc=desc,photo=photo,capacity=capacity)
            return redirect("/admin") 
    return render(request,"add_course.html")

def edit_state(request,id,state):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")
    user = User.objects.get(id=id)
    if user.course.capacity == len(user.course.users.all().filter(state='approve')):
        messages.error(request,f'{user.course.name} course is full')
        #state var here is approve, we need to change to pending
        state=user.state
    user.state = state
    user.save()
    return redirect('/admin')

def apply_course(request,id):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")
    if request.method =='POST':
        user = User.objects.get(id=request.session["userId"])
        if not user.course or  user.state == 'decline':
            course=Course.objects.get(id=id)
            user.course=course
            user.state="pending"
            user.save()
            return redirect(f'/student_profile/{user.id}')
        else: #user already applied to another course 
            messages.error(request, f"you already applied to {user.course.name} course")
            return redirect(f'/student_profile/{user.id}')
    return redirect(f'/student_profile/{user.id}')

def show_student(request,id):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")
    context={
        'user':User.objects.get(id=id),
        'courses':Course.objects.all(),
    }
    return render(request,'student_profile.html',context)

def delete_course(request,id):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")
    Course.objects.get(id=id).delete()
    return redirect('/admin')

def edit_course(request,id):
    if "userId" not in request.session:
        return HttpResponse("Please authenticate first")
    course = Course.objects.get(id=id)
    if request.method == "POST":
        course.name = request.POST["name"]
        course.desc = request.POST["desc"]
        if len(course.users.filter(state="approve"))<=int(request.POST["capacity"]):
            course.capacity=request.POST["capacity"]
        else:
            messages.error(request,"The new seats number is less than the number of applicants.")
            return redirect(f'/edit_course/{course.id}')

        if request.FILES.get('photo'):
            course.photo = request.FILES['photo']
        course.save()
        return redirect('/admin')
    
    context={
        'course':course
    }
    return render(request,'edit_course.html',context)

def show_students_course(request,id):
    context={
        'course':Course.objects.get(id=id),
        'students':Course.objects.get(id=id).users.filter(state='approve')
        }
    return render(request,'shows_student_course.html',context)

def edit_profile(request):
    this_user=User.objects.get(id=request.session["userId"])
    if request.method == "POST":
        this_user.first_name=request.POST["first_name"]
        this_user.last_name=request.POST["last_name"]
        
        # check if course was changed before assign 
        if "course" in request.POST:
            this_course=Course.objects.get(id=request.POST["course"])
            this_user.course=this_course
        
        #check if cv was upladed
        if request.FILES.get('cv'):
            errors = User.objects.file_validatior(request.FILES['cv'])
            if len(errors) > 0:
                for key, errorMessage in errors.items():
                    messages.error(request, errorMessage)
                return redirect(f'/student_profile/{this_user.id}')
            else:
                this_user.cv = request.FILES['cv']
                #messages.success(request, 'CV is added successfully')
        
        #if no cv in the db
        elif this_user.cv =='Empty':
            messages.error(request,"You did not upload your CV")
        this_user.save()
        messages.success(request, 'your profile updated successfully')
    return redirect(f'/student_profile/{this_user.id}')

def add_message(request):
    if request.method == "POST":
        name=request.POST["name"]
        email=request.POST["email"]
        msg=request.POST["message"]
        Message.objects.create(name=name,email=email,message=msg)
        request.session["sucess_msg"]="your message has been sent!"
    return redirect("/")   

def show_message(request):
    msg=Message.objects.filter(read=False)
    request.session["msgs"]=len(msg)
    context={
        "msgs":Message.objects.filter(read=False)
    }
    return render(request,"show_message.html",context)

def read_message(request , id):
    msg=Message.objects.filter(read=False)
    request.session["msgs"]=len(msg)
    msg=Message.objects.get(id=id)
    msg.read=True
    msg.save()
    return redirect('/show_message')


def logout(request):
    request.session.clear()
    # messages.success(request, "You have been logged out!")
    return redirect("/")
